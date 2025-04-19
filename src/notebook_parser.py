# src/notebook_parser.py
from dataclasses import dataclass
from bs4 import BeautifulSoup


class NotebookParseError(Exception):
    """Exception raised when parsing notebook HTML fails"""
    pass


@dataclass
class NotebookParseResult:
    """Result of parsing a notebook HTML file"""
    book_title: str
    notes: list[str]
    total_notes: int

    def to_dict(self) -> dict:
        """Convert the parse result to a dictionary"""
        return {
            "book_title": self.book_title,
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
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract book title
        book_title_elem = soup.find(class_='bookTitle')
        if not book_title_elem:
            raise NotebookParseError("Could not find book title in HTML content")
        book_title = book_title_elem.text.strip()

        # Extract all notes
        notes = []
        note_elements = soup.find_all(class_='noteText')
        if not note_elements:
            raise NotebookParseError("No notes found in HTML content")

        for note in note_elements:
            notes.append(note.text.strip())

        return NotebookParseResult(
            book_title=book_title,
            notes=notes,
            total_notes=len(notes)
        )

    except NotebookParseError:
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        # Wrap any other exceptions in our custom exception
        raise NotebookParseError(f"Error parsing HTML content: {str(e)}") from e
