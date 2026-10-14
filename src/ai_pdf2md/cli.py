import argparse
import sys
from pathlib import Path

from ai_pdf2md import __version__


def _convert(args: argparse.Namespace) -> int:
    from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.base_models import InputFormat

    input_path = Path(args.input)
    if not input_path.is_file():
        print(f"error: no such file: {input_path}", file=sys.stderr)
        return 1

    device = {
        "cpu": AcceleratorDevice.CPU,
        "cuda": AcceleratorDevice.CUDA,
        "auto": AcceleratorDevice.AUTO,
    }[args.device]

    pipeline_options = PdfPipelineOptions()
    pipeline_options.accelerator_options = AcceleratorOptions(device=device)

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )

    result = converter.convert(str(input_path))

    filtered = []
    if not args.keep_repeated_headers:
        from ai_pdf2md.furniture import filter_running_furniture, format_note

        filtered = filter_running_furniture(result.document)

    markdown = result.document.export_to_markdown()
    if filtered:
        note = format_note(filtered)
        markdown = note + "\n\n" + markdown
        print(note)

    output_path = Path(args.output) if args.output else input_path.with_suffix(".md")
    output_path.write_text(markdown, encoding="utf-8")
    print(f"wrote {output_path}")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ai-pdf2md", description="Convert a PDF into AI-friendly Markdown"
    )
    parser.add_argument("--version", action="version", version=__version__)

    subparsers = parser.add_subparsers(dest="command", required=True)

    convert_parser = subparsers.add_parser("convert", help="Convert a PDF to Markdown")
    convert_parser.add_argument("input", help="Path to the input PDF")
    convert_parser.add_argument(
        "-o", "--output", help="Output .md path (default: same name as input, .md extension)"
    )
    convert_parser.add_argument(
        "--device",
        choices=["cpu", "cuda", "auto"],
        default="cpu",
        help="Which device to run the layout/OCR models on (default: cpu)",
    )
    convert_parser.add_argument(
        "--keep-repeated-headers",
        action="store_true",
        help="Do not filter repeated running headers/footers (filtering is on by default)",
    )
    convert_parser.set_defaults(func=_convert)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
