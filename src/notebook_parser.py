# src/notebook_parser.py
from bs4 import BeautifulSoup

def parse_notebook_html(html_content):
    """
    Parse the notebook HTML content and return data in JSON format.

    Args:
        html_content (str): HTML content as string

    Returns:
        dict: Dictionary containing book title and notes
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract book title
        book_title_elem = soup.find(class_='bookTitle')
        book_title = book_title_elem.text.strip() if book_title_elem else "Title not found"

        # Extract all notes
        notes = []
        note_elements = soup.find_all(class_='noteText')
        for note in note_elements:
            notes.append(note.text.strip())

        # Create JSON structure
        output_data = {
            "book_title": book_title,
            "notes": notes,
            "total_notes": len(notes)
        }

        return output_data

    except Exception as e:
        return {"error": f"Error parsing HTML content: {str(e)}"}