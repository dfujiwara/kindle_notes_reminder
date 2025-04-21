from src.llm_interface import LLMClientInterface
from src.notebook_parser import NotebookParseResult

async def get_additional_context(llm_client: LLMClientInterface, parsed_result: NotebookParseResult) -> str:
    """
    Get additional context from OpenAI based on the parsed notebook result.

    :param llm_client: An instance of LLMClientInterface to get responses.
    :param parsed_result: The result of parsing the notebook.
    :return: Additional context as a string.
    """
    prompt = f"Based on the following notes from the notebook titled '{parsed_result.book_title}': {parsed_result.notes}, can you provide additional context or insights?"
    response = await llm_client.get_response(prompt)
    return response
