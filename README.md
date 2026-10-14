# ai-pdf2md

Convert a PDF into Markdown that keeps its structure (headings, tables, lists), so that AI models can read it more accurately than plain extracted text.

```bash
ai-pdf2md convert report.pdf               # writes report.md
ai-pdf2md convert report.pdf -o out.md     # choose the output path
ai-pdf2md convert report.pdf --device cuda # use a GPU for the layout and OCR models
```

## How it works

ai-pdf2md is a thin command-line wrapper around [Docling](https://github.com/docling-project/docling), an open-source document-conversion library. Docling runs small local vision models to find headings, paragraphs, tables, and pictures on each page, and to read scanned pages with OCR. The result is exported as Markdown.

- **Local only.** No cloud API and no API keys. Nothing is sent over the network during conversion.
- **Models download once.** The first run downloads the layout, table-structure, and (if needed) OCR models from Hugging Face. They are cached afterwards.
- **CPU by default.** Pass `--device cuda` to use a GPU, or `--device auto` to let Docling choose.

## Repeated header and footer removal

Docling sometimes labels a line that repeats on every page, such as a classification marking or a copyright notice, as a body heading. That pollutes any heading-based outline built from the output.

ai-pdf2md detects short text that appears at the same position on many pages and removes it from the output. It adds a note at the top of the Markdown listing what was removed and how many pages it appeared on, and prints the same note to stdout, so nothing disappears silently.

If a conversion removes real content, run it again with `--keep-repeated-headers`.

## Requirements

- Python 3.10 or newer
- Several hundred megabytes of disk space for the Docling models, plus PyTorch

## Install

```bash
pip install -e .
```

Docling depends on PyTorch, so the first install is large.

## Limits

- Output quality depends on Docling's models. Complex layouts, unusual fonts, and handwriting may need manual review.
- Scanned PDFs are much slower than text-based PDFs because OCR runs on every page.

## Third-party components

| Component | Purpose | Licence |
|---|---|---|
| [Docling](https://github.com/docling-project/docling) and its `docling-*` packages | PDF parsing and conversion pipeline | MIT |
| PyTorch, Transformers | Model runtime | Apache-2.0 |
| Layout and table-structure models from Hugging Face (`docling-project/*`) | Local models downloaded at runtime | Check each model card |
| NVIDIA CUDA libraries (installed by PyTorch on Linux) | GPU support | NVIDIA proprietary licence |

The NVIDIA libraries are installed from PyPI by users and are not bundled with this project. If you package ai-pdf2md with those libraries included, read NVIDIA's terms first.

## Development

```bash
python3 -m venv ~/.venvs/ai-pdf2md-dev
~/.venvs/ai-pdf2md-dev/bin/pip install -e ".[dev]"
~/.venvs/ai-pdf2md-dev/bin/python -m pytest -q
```

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md).

## Licence

MIT. See [LICENSE](LICENSE).
