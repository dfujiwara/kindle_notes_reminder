# test_notebook_parser.py
import pytest
from .notebook_parser import parse_notebook_html, NotebookParseError


def test_parse_notebook_html_valid():
    html_content = """
    <html>
        <head><title>Test Notebook</title></head>
        <body>
            <div class="bookTitle">Test Book Title</div>
            <div class="authors">Last, First</div>
            <div class="noteText">First note</div>
            <div class="noteText">Second note</div>
        </body>
    </html>
    """
    result = parse_notebook_html(html_content)
    assert result.book_title == "Test Book Title"
    assert result.authors_str == "Last, First"
    assert result.notes == ["First note", "Second note"]
    assert result.total_notes == 2


def test_parse_notebook_html_missing_title():
    html_content = """
    <html>
        <head><title>Test Notebook</title></head>
        <body>
            <div class="noteText">First note</div>
        </body>
    </html>
    """
    with pytest.raises(
        NotebookParseError, match="Could not find book title in HTML content"
    ):
        parse_notebook_html(html_content)


def test_parse_notebook_html_missing_authors():
    html_content = """
    <html>
        <head><title>Test Notebook</title></head>
        <body>
            <div class="bookTitle">Test Book Title</div>
            <div class="noteText">First note</div>
        </body>
    </html>
    """
    with pytest.raises(
        NotebookParseError, match="Could not find authors in HTML content"
    ):
        parse_notebook_html(html_content)


def test_parse_notebook_html_no_notes():
    html_content = """
    <html>
        <head><title>Test Notebook</title></head>
        <body>
            <div class="bookTitle">Test Book Title</div>
            <div class="authors">Last, First</div>
        </body>
    </html>
    """
    with pytest.raises(NotebookParseError, match="No notes found in HTML content"):
        parse_notebook_html(html_content)


def test_parse_notebook_html_malformed():
    html_content = "<html><head><title>Test Notebook</title></head><body><div class='bookTitle'></div></body>"
    with pytest.raises(NotebookParseError):
        parse_notebook_html(html_content)
