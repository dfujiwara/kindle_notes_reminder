from dataclasses import dataclass
from typing import AsyncGenerator
from src.llm_interface import LLMClientInterface, LLMPromptResponse
from src.repositories.models import BookResponse, NoteRead
from src.prompts import create_context_prompt, SYSTEM_INSTRUCTIONS


@dataclass
class StreamedContextChunk:
    """
    Represents a single item yielded from streaming additional context.

    This unified type can represent either:
    - A chunk of content as it arrives (is_complete=False)
    - The final complete result with metadata (is_complete=True)
    """

    content: str
    is_complete: bool = False
    llm_prompt_response: LLMPromptResponse | None = None


async def get_additional_context_stream(
    llm_client: LLMClientInterface, book: BookResponse, note: NoteRead
) -> AsyncGenerator[StreamedContextChunk, None]:
    """
    Stream additional context and return final result with metadata.

    This function yields StreamedContextChunk objects. Each chunk has:
    - content: The text content (chunk or full response)
    - is_complete: False for chunks, True for the final result
    - llm_prompt_response: Only present when is_complete=True

    :param llm_client: An instance of LLMClientInterface to get responses.
    :param book: The Book model containing the book information.
    :param note: The Note model containing the note content.
    :yield: StreamedContextChunk objects for each chunk and final result.
    """
    prompt = create_context_prompt(book.title, note.content)
    instruction = SYSTEM_INSTRUCTIONS["context_provider"]

    full_response = ""
    async for chunk in llm_client.get_response_stream(prompt, instruction):
        full_response += chunk
        yield StreamedContextChunk(content=chunk, is_complete=False)

    # Yield the final result with metadata
    llm_prompt_response = LLMPromptResponse(
        response=full_response, prompt=prompt, system=instruction
    )
    yield StreamedContextChunk(
        content=full_response,
        is_complete=True,
        llm_prompt_response=llm_prompt_response,
    )
