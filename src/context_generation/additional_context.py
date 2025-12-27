from dataclasses import dataclass
from typing import AsyncGenerator
from src.llm_interface import LLMClientInterface, LLMPromptResponse
from src.prompts import create_chunk_context_prompt, SYSTEM_INSTRUCTIONS


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
    llm_client: LLMClientInterface, prompt: str, system_instruction: str
) -> AsyncGenerator[StreamedContextChunk, None]:
    """
    Stream additional context from an LLM given a prompt and system instruction.

    This function yields StreamedContextChunk objects. Each chunk has:
    - content: The text content (chunk or full response)
    - is_complete: False for chunks, True for the final result
    - llm_prompt_response: Only present when is_complete=True

    :param llm_client: An instance of LLMClientInterface to get responses.
    :param prompt: The prompt to send to the LLM.
    :param system_instruction: The system instruction for the LLM.
    :yield: StreamedContextChunk objects for each chunk and final result.
    """
    full_response = ""
    async for chunk in llm_client.get_response_stream(prompt, system_instruction):
        full_response += chunk
        yield StreamedContextChunk(content=chunk, is_complete=False)

    # Yield the final result with metadata
    llm_prompt_response = LLMPromptResponse(
        response=full_response, prompt=prompt, system=system_instruction
    )
    yield StreamedContextChunk(
        content=full_response,
        is_complete=True,
        llm_prompt_response=llm_prompt_response,
    )


async def get_additional_context_stream_for_chunk(
    llm_client: LLMClientInterface, url_title: str, chunk_content: str
) -> AsyncGenerator[StreamedContextChunk, None]:
    """
    Stream additional context for a URL chunk.

    Generates context for a specific chunk from a URL by creating a prompt
    from the URL title and chunk content, then streaming the response.

    :param llm_client: An instance of LLMClientInterface to get responses.
    :param url_title: The title of the URL/webpage.
    :param chunk_content: The content of the chunk.
    :yield: StreamedContextChunk objects for each chunk and final result.
    """
    prompt = create_chunk_context_prompt(url_title, chunk_content)
    system_instruction = SYSTEM_INSTRUCTIONS["context_provider"]
    async for chunk in get_additional_context_stream(
        llm_client, prompt, system_instruction
    ):
        yield chunk
