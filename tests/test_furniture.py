"""Tests for running header/footer (furniture) filtering.

Uses synthetic in-process DoclingDocuments -- fast, offline, no PDF or model
download needed. See docs/design-strip-running-furniture.md, test plan items 1-9.
"""

from types import SimpleNamespace

from docling_core.types.doc.base import BoundingBox, CoordOrigin, Size
from docling_core.types.doc.document import (
    ContentLayer,
    DoclingDocument,
    ProvenanceItem,
)

from ai_pdf2md.furniture import filter_running_furniture, format_note

PAGE_W, PAGE_H = 612.0, 792.0
WATERMARK = "TLP AMBER + STRICT"


def make_doc(pages: int) -> DoclingDocument:
    doc = DoclingDocument(name="test")
    for p in range(1, pages + 1):
        doc.add_page(page_no=p, size=Size(width=PAGE_W, height=PAGE_H))
    return doc


def add_heading_at(doc, text, page, y_center, level=2):
    """Add a heading whose bbox vertical center is y_center (0=top, 1=bottom)."""
    half = 10.0
    bbox = BoundingBox(
        l=50,
        t=y_center * PAGE_H - half,
        r=562,
        b=y_center * PAGE_H + half,
        coord_origin=CoordOrigin.TOPLEFT,
    )
    prov = ProvenanceItem(page_no=page, bbox=bbox, charspan=(0, len(text)))
    return doc.add_heading(text=text, level=level, prov=prov)


# --- test plan item 1: the real-case shape ---------------------------------

def test_repeated_watermark_heading_is_stripped():
    doc = make_doc(20)
    items = [add_heading_at(doc, WATERMARK, p, 0.04) for p in range(1, 21)]
    add_heading_at(doc, "1. Introduction", 1, 0.3, level=1)

    filtered = filter_running_furniture(doc)

    assert filtered == [(WATERMARK, 20, 20)]
    assert all(i.content_layer == ContentLayer.FURNITURE for i in items)
    md = doc.export_to_markdown()
    assert WATERMARK not in md
    assert "1. Introduction" in md


# --- regression: mixed in/out-of-cluster items sharing the same text -------
# (codex finding on task #46: rule 3 gates the GROUP on >=80% cluster share,
# but only the in-cluster occurrences may be stripped)

def test_legit_same_text_body_heading_survives_alongside_real_furniture():
    doc = make_doc(20)
    headers = [add_heading_at(doc, "CONFIDENTIAL", p, 0.04) for p in range(1, 21)]
    # Same text, but a legit mid-page body heading (e.g. a section title).
    legit = add_heading_at(doc, "CONFIDENTIAL", 5, 0.5, level=1)

    filtered = filter_running_furniture(doc)

    assert filtered == [("CONFIDENTIAL", 20, 20)]
    assert all(i.content_layer == ContentLayer.FURNITURE for i in headers)
    assert legit.content_layer == ContentLayer.BODY
    md = doc.export_to_markdown()
    assert md.count("CONFIDENTIAL") == 1  # only the legit heading survives


def test_straddling_item_is_never_partially_stripped():
    doc = make_doc(20)
    for p in range(1, 21):
        add_heading_at(doc, "CONFIDENTIAL", p, 0.04)
    # One item whose provs straddle: one occurrence in the dominant top
    # cluster, one mid-page -> ambiguous, must stay BODY.
    straddler = add_heading_at(doc, "CONFIDENTIAL", 3, 0.04)
    mid_bbox = BoundingBox(
        l=50, t=0.5 * PAGE_H - 10, r=562, b=0.5 * PAGE_H + 10,
        coord_origin=CoordOrigin.TOPLEFT,
    )
    straddler.prov.append(
        ProvenanceItem(page_no=4, bbox=mid_bbox, charspan=(0, 12))
    )

    filtered = filter_running_furniture(doc)

    assert filtered == [("CONFIDENTIAL", 20, 20)]  # straddler's pages not counted
    assert straddler.content_layer == ContentLayer.BODY
    assert straddler.text in doc.export_to_markdown()


# --- regression: mixed page heights, same absolute header position ---------
# (codex re-review finding on the real 61-page government PDF: portrait y=0.036 vs
# landscape y=0.050 straddled the fixed 0.05 bin edge, splitting one physical
# header into two bins -- 4 landscape-page headers escaped filtering)

def test_mixed_page_heights_same_absolute_header_is_one_cluster():
    portrait_h, landscape_h = 841.9, 595.3  # real A4 dims from the government PDF
    doc = DoclingDocument(name="mixed")
    for p in range(1, 21):
        h = landscape_h if p > 16 else portrait_h
        doc.add_page(page_no=p, size=Size(width=PAGE_W, height=h))
    items = []
    for p in range(1, 21):
        h = landscape_h if p > 16 else portrait_h
        top = 30.0  # same absolute on-page position on every page
        bbox = BoundingBox(
            l=50, t=top - 7.5, r=562, b=top + 7.5,
            coord_origin=CoordOrigin.TOPLEFT,
        )
        prov = ProvenanceItem(page_no=p, bbox=bbox, charspan=(0, len(WATERMARK)))
        items.append(doc.add_heading(text=WATERMARK, level=2, prov=prov))

    filtered = filter_running_furniture(doc)

    assert filtered == [(WATERMARK, 20, 20)]
    assert all(i.content_layer == ContentLayer.FURNITURE for i in items)
    assert WATERMARK not in doc.export_to_markdown()


# --- regression: dense single-page cluster is not furniture ----------------
# (codex 3rd finding on task #46: rule 2/near_universal gated on whole-group
# distinct pages, so a 12x-on-page-1 cluster cleared the cross-page threshold
# via outlier pages -- design explicitly says "a phrase repeated 10x on one
# page is not furniture")

def test_dense_single_page_cluster_never_stripped():
    doc = make_doc(10)
    dense = [add_heading_at(doc, "NOTE", 1, 0.04) for _ in range(12)]
    outliers = [add_heading_at(doc, "NOTE", p, 0.5) for p in (2, 3, 4)]

    assert filter_running_furniture(doc) == []
    assert all(i.content_layer == ContentLayer.BODY for i in dense + outliers)
    assert doc.export_to_markdown().count("NOTE") == 15


# --- test plan item 2: legit repeated subsection headings ------------------

def test_legit_repeated_subsection_headings_kept():
    doc = make_doc(20)
    for i, p in enumerate(range(1, 13)):
        add_heading_at(doc, "Recommendation", p, 0.3 + 0.05 * (i % 5))

    assert filter_running_furniture(doc) == []
    assert "Recommendation" in doc.export_to_markdown()


# --- test plan item 3: short-doc immunity (absolute floor of 4 pages) ------

def test_short_doc_never_triggers():
    doc = make_doc(3)
    for p in range(1, 4):
        add_heading_at(doc, WATERMARK, p, 0.05)

    assert filter_running_furniture(doc) == []


# --- test plan item 4: threshold scales with document length ---------------

def test_long_doc_needs_proportionally_many_pages():
    doc = make_doc(61)
    for p in range(1, 9):  # 8 pages < ceil(0.4 * 61) = 25
        add_heading_at(doc, WATERMARK, p, 0.05)

    assert filter_running_furniture(doc) == []


# --- test plan item 5: alternating (odd/even) footer ------------------------

def test_alternating_footer_is_caught():
    doc = make_doc(30)
    for p in range(2, 31, 2):  # even pages only: 15 >= ceil(0.4 * 30) = 12
        add_heading_at(doc, "Draft - not for release", p, 0.97)

    filtered = filter_running_furniture(doc)

    assert filtered == [("Draft - not for release", 15, 30)]
    assert "Draft - not for release" not in doc.export_to_markdown()


# --- test plan item 6: long repeated text is not furniture ------------------

def test_long_repeated_text_kept():
    text = "This fairly long sentence keeps on repeating verbatim on every page of the document today"
    assert len(text.split()) > 10
    doc = make_doc(20)
    for p in range(1, 21):
        add_heading_at(doc, text, p, 0.05)

    assert filter_running_furniture(doc) == []


# --- test plan item 7: no provenance -> never flagged, no crash -------------

def test_items_without_provenance_never_flagged():
    doc = make_doc(20)
    for _ in range(20):
        doc.add_heading(text=WATERMARK, level=2)  # prov=None

    assert filter_running_furniture(doc) == []
    assert WATERMARK in doc.export_to_markdown()


# --- test plan item 8: disclosure note rendering ----------------------------

def test_format_note_single_line_with_counts():
    from ai_pdf2md.furniture import FilteredEntry

    note = format_note([FilteredEntry("TLP AMBER + STRICT", 61, 61)])

    assert note.count("\n") == 0
    assert note.startswith("> [ai-pdf2md] Filtered repeated running header/footer text:")
    assert '"TLP AMBER + STRICT" (61/61 pages)' in note


# --- test plan items 8/9: CLI-level filtering, note, and opt-out ------------

class _FakeConverter:
    def __init__(self, format_options=None):
        pass

    def convert(self, path):
        return SimpleNamespace(document=self._doc)

    _doc = None


def _run_convert(monkeypatch, tmp_path, keep_flag):
    import docling.document_converter
    from ai_pdf2md import cli

    doc = make_doc(20)
    for p in range(1, 21):
        add_heading_at(doc, WATERMARK, p, 0.04)
    add_heading_at(doc, "Real Content", 1, 0.5, level=1)

    _FakeConverter._doc = doc
    monkeypatch.setattr(docling.document_converter, "DocumentConverter", _FakeConverter)

    input_pdf = tmp_path / "in.pdf"
    input_pdf.write_bytes(b"%PDF-1.4 fake")
    output_md = tmp_path / "out.md"
    args = SimpleNamespace(
        input=str(input_pdf),
        output=str(output_md),
        device="cpu",
        keep_repeated_headers=keep_flag,
    )
    assert cli._convert(args) == 0
    return output_md.read_text(encoding="utf-8")


def test_convert_filters_by_default_and_prepends_note(monkeypatch, tmp_path):
    md = _run_convert(monkeypatch, tmp_path, keep_flag=False)

    assert WATERMARK not in md.replace('"' + WATERMARK + '"', "")  # only in the note
    assert md.startswith("> [ai-pdf2md] Filtered repeated running header/footer text:")
    assert '"TLP AMBER + STRICT" (20/20 pages)' in md.splitlines()[0]
    assert "Real Content" in md


def test_convert_keep_repeated_headers_opt_out(monkeypatch, tmp_path):
    md = _run_convert(monkeypatch, tmp_path, keep_flag=True)

    assert WATERMARK in md
    assert "[ai-pdf2md] Filtered" not in md


def test_convert_no_note_when_nothing_filtered(monkeypatch, tmp_path):
    import docling.document_converter
    from ai_pdf2md import cli

    doc = make_doc(2)
    add_heading_at(doc, "Only Content", 1, 0.5, level=1)
    _FakeConverter._doc = doc
    monkeypatch.setattr(docling.document_converter, "DocumentConverter", _FakeConverter)

    input_pdf = tmp_path / "in.pdf"
    input_pdf.write_bytes(b"%PDF-1.4 fake")
    output_md = tmp_path / "out.md"
    args = SimpleNamespace(
        input=str(input_pdf),
        output=str(output_md),
        device="cpu",
        keep_repeated_headers=False,
    )
    assert cli._convert(args) == 0
    md = output_md.read_text(encoding="utf-8")
    assert "[ai-pdf2md] Filtered" not in md
    assert "Only Content" in md
