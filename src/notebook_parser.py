# src/notebook_parser.py
import logging
from dataclasses import dataclass
from typing import Any
from bs4 import BeautifulSoup

# Configure logging for this module
logger = logging.getLogger(__name__)


class NotebookParseError(Exception):
    """Exception raised when parsing notebook HTML fails"""

    pass


@dataclass
class NotebookParseResult:
    """Result of parsing a notebook HTML file"""

    book_title: str
    authors_str: str
    notes: list[str]
    total_notes: int

    def to_dict(self) -> dict[str, Any]:
        """Convert the parse result to a dictionary"""
        return {
            "book_title": self.book_title,
            "authors_str": self.authors_str,
            "notes": self.notes,
            "total_notes": self.total_notes,
        }


def parse_notebook_html(html_content: str) -> NotebookParseResult:
    """
    Parse the notebook HTML content and return structured result.

    Args:
        html_content (str): HTML content as string

    Returns:
        NotebookParseResult: Structured result containing parsed data

    Raises:
        NotebookParseError: If parsing fails
    """
    try:
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract book title
        book_title_elem = soup.find(class_="bookTitle")
        if not book_title_elem:
            raise NotebookParseError("Could not find book title in HTML content")
        book_title = book_title_elem.text.strip()

        # Extract author
        authors_elem = soup.find(class_="authors")
        if not authors_elem:
            raise NotebookParseError("Could not find authors in HTML content")
        authors_str = authors_elem.text.strip()

        # Extract all notes
        notes: list[str] = []
        note_elements = soup.find_all(class_="noteText")
        if not note_elements:
            raise NotebookParseError("No notes found in HTML content")

        for note in note_elements:
            notes.append(note.text.strip())

        return NotebookParseResult(
            book_title=book_title,
            authors_str=authors_str,
            notes=notes,
            total_notes=len(notes),
        )

    except NotebookParseError as e:
        logger.error("NotebookParseError: %s", str(e))  # Log the parsing error
        raise
    except Exception as e:
        logger.error(
            "Unexpected error during parsing: %s", str(e)
        )  # Log unexpected errors
        raise NotebookParseError(f"Error parsing HTML content: {str(e)}") from e
