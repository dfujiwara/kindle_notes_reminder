from src.llm_interface import LLMClientInterface
from src.repositories.models import Book, Note


async def get_additional_context(
    llm_client: LLMClientInterface, book: Book, note: Note
) -> str:
    """
    Get additional context from OpenAI based on the book and note models.

    :param llm_client: An instance of LLMClientInterface to get responses.
    :param book: The Book model containing the book information.
    :param note: The Note model containing the note content.
    :return: Additional context as a string.
    """
    prompt = f"Based on the following notes from the notebook titled '{book.title}': {note.content}, can you provide additional context or insights?"
    instruction = """You are helping a user remember the concept highlighted in a given book. Please provide some additional context and use some examples so that it will be easier for the user to understand it more."""
    response = await llm_client.get_response(prompt, instruction)
    return response
