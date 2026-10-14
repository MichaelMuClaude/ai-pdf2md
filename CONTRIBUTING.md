# Contributing to ai-pdf2md

Thanks for helping. Humans and AI agents are both welcome. The detailed rules for agents are in [AGENTS.md](AGENTS.md).

## Ground rules

- Keep the tool local: no cloud APIs and no uploads of document content.
- Never remove content silently. Filtering must always be reported.
- Use synthetic test data only. Do not commit real PDFs or their output.
- Keep changes small, and add a test for every behaviour change.

## Running the tests

```bash
python3 -m venv ~/.venvs/ai-pdf2md-dev
~/.venvs/ai-pdf2md-dev/bin/pip install -e ".[dev]"
~/.venvs/ai-pdf2md-dev/bin/python -m pytest -q
```

The first install downloads PyTorch, so it takes a while.

Continuous integration runs the test suite on Python 3.10 and 3.13.

## Opening a pull request

1. Fork the repository and create a branch with a descriptive name.
2. Make the change with tests.
3. Describe what changed, why, and which tests you ran. For filter changes, describe the cases you checked.
4. If an AI agent wrote or helped write the change, say so and name the tool and model.

## Reporting bugs

Open an issue with the command, the output you got, and the output you expected. Describe the PDF's type (text-based or scanned) and layout in general terms. Do not attach a real document. If you need to show a problem, make a synthetic PDF that reproduces it.

## Licence

By contributing, you agree that your contribution is released under the MIT licence in [LICENSE](LICENSE).
