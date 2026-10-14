---
name: ai-pdf2md
description: Convert a PDF into structure-preserving Markdown (headings, tables, lists) so that an agent can read it accurately. Runs locally with open models; no cloud API. Use for batch conversion or scripted use; for a single short PDF, reading it directly may be simpler.
---

# ai-pdf2md

## What it does

Converts a PDF to Markdown, keeping headings, tables, and lists. It uses local models through Docling, so no data leaves the machine during conversion.

## Usage

```bash
ai-pdf2md convert input.pdf                   # writes input.md next to the PDF
ai-pdf2md convert input.pdf -o output.md      # choose the output path
ai-pdf2md convert input.pdf --device cuda     # use a GPU (default is cpu)
ai-pdf2md convert input.pdf --keep-repeated-headers   # turn off running header/footer removal
```

- **Success:** exit code 0, and the output path is printed.
- **Failure:** a message on stderr and a non-zero exit code.

## Running header and footer removal

By default, text that repeats at the same position on many pages (for example a classification marking or copyright line) is removed. A note at the top of the output lists what was removed and on how many pages. If the note shows that real content was removed, run the conversion again with `--keep-repeated-headers`.

## When to use it

- Batch conversion of several PDFs, or conversion inside a script.
- Documents that need a clean, structured outline for later processing.

## When not to use it

- A single short PDF that can be read directly. Reading it directly is often quicker.

## Notes

- The first run downloads models from Hugging Face. Later runs use the cache.
- Scanned PDFs are slow because OCR runs on every page.
- Table and layout quality depends on the models. Check the output for complex layouts.
