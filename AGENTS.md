# AGENTS.md — guide for AI agents contributing to ai-pdf2md

This file is for AI coding agents that read, test, or change this project. The human-facing rules are in [CONTRIBUTING.md](CONTRIBUTING.md).

## What this project is

`ai-pdf2md` is a command-line wrapper around Docling. It converts a PDF into Markdown, removes repeated running headers and footers, and writes a note listing anything it removed. It runs local models only.

## Promises to keep

1. **Local only.** Do not add calls to cloud APIs, telemetry, or any upload of document content.
2. **Visible filtering.** Anything the header/footer filter removes must be reported in the output note and on stdout. Never remove content silently.
3. **Opt-out stays available.** `--keep-repeated-headers` must always return the unfiltered output.
4. **Stable CLI.** Keep the `convert` subcommand, its flags, and the exit codes (0 for success, non-zero for failure) backward compatible.
5. **Default device is CPU.** GPU use must stay opt-in through `--device`.

## Layout

```
src/ai_pdf2md/
  cli.py         argument parsing, Docling setup, output writing
  furniture.py   detection and removal of repeated running headers and footers
  __init__.py    version
tests/
  test_cli.py        CLI behaviour
  test_furniture.py  filter behaviour, using synthetic document items
SKILL.md         usage guide for agents that call the tool
```

## Setup and checks

Keep the virtualenv outside any folder synced by a file-sync tool.

```bash
python3 -m venv ~/.venvs/ai-pdf2md-dev
~/.venvs/ai-pdf2md-dev/bin/pip install -e ".[dev]"
~/.venvs/ai-pdf2md-dev/bin/python -m pytest -q
```

The tests in `test_furniture.py` build synthetic Docling documents, so they do not need to download models. Keep them that way. A test that needs a real PDF must say so and must not run in CI.

## Rules for changes

- **Keep changes small.** One fix or feature per pull request.
- **Add a test for each behaviour change.** For filter changes, include a case that must not be filtered (legitimate repeated text such as a repeated subsection heading) as well as a case that must be.
- **Do not put real documents in the repository.** Test data must be synthetic. Do not commit PDFs or Markdown output from real documents.
- **Do not add dependencies** unless they are necessary. Docling is already large.
- **Keep the Python floor at 3.10.**
- **Do not change the filter's default behaviour** without an issue and a discussion, because it changes every user's output.

## Pull request description

Include:

- What changed and why, in two or three sentences.
- The test command you ran and its result.
- For filter changes: the false positives and false negatives you checked, and how you checked them.
- A line stating that the change was produced with AI assistance, and which tool and model you used.

## Security

Do not report vulnerabilities in a public issue. Use a private security advisory on GitHub.

## Good first tasks for agents

- Add a unit test for an edge case in `furniture.py` that is not covered yet.
- Improve the wording of the note that the filter prints.
- Check that `README.md` and `SKILL.md` match the actual CLI flags.
