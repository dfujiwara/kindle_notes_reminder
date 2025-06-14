# scripts/parse_notebook.py
import sys
import json
import argparse
from src.notebook_parser import parse_notebook_html, NotebookParseError


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Parse notebook HTML file to extract book title and notes in JSON format."
    )
    parser.add_argument("file_path", help="Path to the notebook HTML file")
    args = parser.parse_args()

    # Read the file
    try:
        with open(args.file_path, "r", encoding="utf-8") as file:
            html_content = file.read()
    except FileNotFoundError:
        print(
            json.dumps(
                {"error": f"File not found at {args.file_path}"},
                ensure_ascii=False,
                indent=2,
            )
        )
        sys.exit(1)
    except Exception as e:
        print(
            json.dumps(
                {"error": f"Error reading file: {str(e)}"}, ensure_ascii=False, indent=2
            )
        )
        sys.exit(1)

    # Parse the HTML content
    try:
        result = parse_notebook_html(html_content)
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    except NotebookParseError as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
