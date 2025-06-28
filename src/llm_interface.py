from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class LLMPromptResponse:
    prompt: str
    response: str
    system: str


class LLMError(Exception):
    """Base exception class for all LLM-related errors"""

    pass


class LLMClientInterface(ABC):
    @abstractmethod
    async def get_response(self, prompt: str, instruction: str) -> str:
        """
        Send a prompt and instruction to the language model and return the response.

        :param prompt: The input prompt to send to the model.
        :return: The model's response as a string.
        :raises LLMError: If there is an error communicating with the LLM service
        """
        pass
