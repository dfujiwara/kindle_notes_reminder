import pytest
from .notebook_processor import process_notebook_result
from .notebook_parser import NotebookParseResult
from src.test_utils import StubBookRepository, StubNoteRepository, StubEmbeddingClient
from src.embedding_interface import EmbeddingError


@pytest.mark.asyncio
async def test_process_notebook_result_success():
    # Setup
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    # Create a sample NotebookParseResult
    result = NotebookParseResult(
        book_title="Sample Book",
        authors_str="Author Name",
        notes=["Note 1", "Note 2"],
        total_notes=2,
    )

    # Call the function
    processed_result = await process_notebook_result(
        result, book_repo, note_repo, embedding_client
    )

    # Assertions
    assert processed_result.book.title == "Sample Book"
    assert processed_result.book.author == "Author Name"
    assert len(processed_result.notes) == 2
    assert processed_result.notes[0].content == "Note 1"
    assert processed_result.notes[1].content == "Note 2"


@pytest.mark.asyncio
async def test_process_notebook_result_return_value():
    # Setup
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient()

    # Create a sample NotebookParseResult
    result = NotebookParseResult(
        book_title="Sample Book",
        authors_str="Author Name",
        notes=["Note 1", "Note 2"],
        total_notes=2,
    )

    # Call the function and get the return value
    returned_value = await process_notebook_result(
        result, book_repo, note_repo, embedding_client
    )

    # Assertions for the book
    assert returned_value.book.id == 1
    assert returned_value.book.title == "Sample Book"
    assert returned_value.book.author == "Author Name"

    # Assertions for the notes
    assert len(returned_value.notes) == 2
    assert returned_value.notes[0].id == 1
    assert returned_value.notes[0].content == "Note 1"
    assert returned_value.notes[1].id == 2
    assert returned_value.notes[1].content == "Note 2"


@pytest.mark.asyncio
async def test_process_notebook_result_embedding_failure():
    # Setup
    book_repo = StubBookRepository()
    note_repo = StubNoteRepository()
    embedding_client = StubEmbeddingClient(should_fail=True)

    # Create a sample NotebookParseResult
    result = NotebookParseResult(
        book_title="Sample Book",
        authors_str="Author Name",
        notes=["Note 1"],
        total_notes=1,
    )

    # Call the function and expect it to raise EmbeddingError
    with pytest.raises(EmbeddingError):
        await process_notebook_result(result, book_repo, note_repo, embedding_client)
