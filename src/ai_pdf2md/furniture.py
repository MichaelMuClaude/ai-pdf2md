"""Detect and filter repeated running headers/footers (page furniture) that
Docling misclassified as body content.

See docs/design-strip-running-furniture.md for the detection rule and the
false-positive analysis. Works on the DoclingDocument BEFORE markdown export:
flagged items are reclassified into ContentLayer.FURNITURE, which
export_to_markdown() excludes by default.
"""

import math
import re
from collections import namedtuple

from docling_core.types.doc.document import ContentLayer

# One filtered text: what it was, on how many distinct pages, out of how many.
FilteredEntry = namedtuple("FilteredEntry", ["text", "page_hits", "total_pages"])

_MAX_WORDS = 10
_MAX_CHARS = 120
_MIN_DISTINCT_PAGES = 4  # absolute floor: short docs can never trigger
_PAGE_RATIO = 0.4  # else fraction of total pages (catches odd/even furniture)
_Y_BIN = 0.05  # normalized page-height tolerance for positional consistency
_Y_CONSISTENCY = 0.8  # densest y cluster must hold this share of hits
_MARGIN_BAND = 0.2  # top/bottom band of the page counts as a margin
_UNIVERSAL_RATIO = 0.9  # or the text appears on this share of all pages

_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", text.strip())


def _occurrences(item, doc):
    """Yield (page_no, y_center) for each provenance record of a text item.

    y_center is the vertical center normalized to [0, 1] of the page height,
    top-left origin. Records without bbox/page info are skipped (never used
    to flag anything).
    """
    for prov in item.prov or []:
        if prov.bbox is None or prov.page_no is None:
            continue
        page = doc.pages.get(prov.page_no)
        if page is None or not page.size.height:
            continue
        tl = prov.bbox.to_top_left_origin(page_height=page.size.height)
        yield prov.page_no, (tl.t + tl.b) / 2 / page.size.height


def _densest_window(ys: list[float], width: float) -> list[float]:
    """Return the sorted points inside the densest sliding window of `width`.

    Boundary-independent replacement for fixed-grid binning: a grid splits
    one physical header across bin edges when page heights differ (portrait
    vs landscape normalizes the same absolute position to y values that can
    straddle a bin edge -- real miss on a 61-page government PDF). The densest
    window of a given width always has a point at its left edge, so scanning
    windows anchored at each point finds the maximum.
    """
    ys = sorted(ys)
    best: list[float] = []
    for i, y0 in enumerate(ys):
        j = i
        while j < len(ys) and ys[j] <= y0 + width:
            j += 1
        if j - i > len(best):
            best = ys[i:j]
    return best


def filter_running_furniture(doc) -> list[FilteredEntry]:
    """Reclassify repeated running-furniture texts into ContentLayer.FURNITURE.

    Returns one FilteredEntry per distinct text that was filtered.
    """
    total_pages = doc.num_pages()

    groups: dict[str, list] = {}
    for item in doc.texts:
        if getattr(item, "content_layer", ContentLayer.BODY) != ContentLayer.BODY:
            continue
        norm = _normalize(getattr(item, "text", "") or "")
        if not norm:
            continue
        groups.setdefault(norm, []).append(item)

    min_pages = max(_MIN_DISTINCT_PAGES, math.ceil(_PAGE_RATIO * total_pages))
    filtered: list[FilteredEntry] = []

    for norm, items in groups.items():
        # Rule 1: short.
        if len(norm) > _MAX_CHARS or len(norm.split()) > _MAX_WORDS:
            continue

        occ = [(item, page, y) for item in items for page, y in _occurrences(item, doc)]
        if not occ:
            continue  # no provenance -> never flag

        # Rule 2 early-out (necessary condition only): if the whole group
        # spans fewer pages than the floor, the cluster certainly does too.
        group_pages = {page for _, page, _ in occ}
        if len(group_pages) < min_pages:
            continue

        # Rule 3: positionally consistent (same vertical band every time).
        cluster = _densest_window([y for _, _, y in occ], _Y_BIN)
        if len(cluster) < _Y_CONSISTENCY * len(occ):
            continue

        # Determine what WOULD be stripped before gating rules 2/4 and
        # before any mutation: ONLY the dominant-cluster occurrences --
        # flagging every occurrence of the text would defeat rule 3 (a
        # legit body heading sharing the furniture's text sits OUTSIDE the
        # cluster and must survive). Conservative for multi-prov items: an
        # item is stripped only if ALL of its occurrences are in the
        # dominant cluster -- never partially strip, since a straddling
        # item is exactly what a false positive looks like.
        lo, hi = cluster[0], cluster[-1]
        item_ys: dict[int, tuple] = {}
        for item, _, y in occ:
            item_ys.setdefault(id(item), (item, []))[1].append(y)
        stripped = [
            item for item, iys in item_ys.values() if all(lo <= y <= hi for y in iys)
        ]
        if not stripped:
            continue

        stripped_ids = {id(item) for item in stripped}
        # hit_pages = pages actually covered by the cluster that will be
        # mutated -- every page-based gate below must use this, NOT the
        # whole-group page set (a dense single-page cluster must not clear
        # the cross-page threshold on pages it doesn't come from; design:
        # "a phrase repeated 10x on one page is not furniture").
        hit_pages = {
            page for item, page, _ in occ if id(item) in stripped_ids
        }

        # Rule 2: frequent across pages, scaled to doc length.
        if len(hit_pages) < min_pages:
            continue

        # Rule 4: at a page margin OR near-universal across pages.
        cluster_center = sum(cluster) / len(cluster)
        at_margin = cluster_center <= _MARGIN_BAND or cluster_center >= 1 - _MARGIN_BAND
        near_universal = len(hit_pages) >= _UNIVERSAL_RATIO * total_pages
        if not (at_margin or near_universal):
            continue

        for item in stripped:
            item.content_layer = ContentLayer.FURNITURE
        filtered.append(FilteredEntry(norm, len(hit_pages), total_pages))

    return filtered


def format_note(filtered: list[FilteredEntry]) -> str:
    """Render the one-line disclosure note prepended to the markdown."""
    parts = ", ".join(f'"{e.text}" ({e.page_hits}/{e.total_pages} pages)' for e in filtered)
    return f"> [ai-pdf2md] Filtered repeated running header/footer text: {parts}."
