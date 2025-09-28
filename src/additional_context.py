from src.llm_interface import LLMClientInterface, LLMPromptResponse
from src.repositories.models import BookResponse, NoteRead
from src.prompts import create_context_prompt, SYSTEM_INSTRUCTIONS


async def get_additional_context(
    llm_client: LLMClientInterface, book: BookResponse, note: NoteRead
) -> LLMPromptResponse:
    """
    Get additional context from OpenAI based on the book and note models.

    :param llm_client: An instance of LLMClientInterface to get responses.
    :param book: The Book model containing the book information.
    :param note: The Note model containing the note content.
    :return: Additional context as a string.
    """
    prompt = create_context_prompt(book.title, note.content)
    instruction = SYSTEM_INSTRUCTIONS["context_provider"]
    response = await llm_client.get_response(prompt, instruction)
    return LLMPromptResponse(response=response, prompt=prompt, system=instruction)
