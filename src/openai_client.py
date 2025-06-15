# src/openai_client.py
import openai
import os
import logging
from openai import APIError, RateLimitError, AuthenticationError
from src.llm_interface import LLMClientInterface, LLMError
from src.types import Embedding
from src.embedding_interface import EmbeddingClientInterface, EmbeddingError

# Configure logging
logger = logging.getLogger(__name__)


class OpenAIClient(LLMClientInterface):
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def get_response(self, prompt: str, instruction: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": prompt},
                ],
            )
            message_content = response.choices[0].message.content
            if message_content is None:
                logger.error("No response from OpenAI.")
                raise LLMError("No response from OpenAI")
            return message_content.strip()
        except RateLimitError:
            logger.warning("Rate limit exceeded.")
            raise LLMError("Rate limit exceeded. Please try again later.")
        except AuthenticationError:
            logger.error("Authentication failed.")
            raise LLMError("Authentication failed. Please check your API key.")
        except APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise LLMError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error during API call.")
            raise LLMError(f"Unexpected error during API call: {str(e)}")


class OpenAIEmbeddingClient(EmbeddingClientInterface):
    def __init__(self, model: str = "text-embedding-3-small"):
        self.model = model
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def generate_embedding(self, content: str) -> Embedding:
        """
        Generate an embedding for the given content using OpenAI's API.

        Args:
            content: The text content to generate an embedding for.

        Returns:
            An embedding vector (list of floats).

        Raises:
            EmbeddingError: If there's an error generating the embedding.
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=content,
            )
            return response.data[0].embedding
        except RateLimitError:
            logger.warning("Rate limit exceeded.")
            raise EmbeddingError("Rate limit exceeded. Please try again later.")
        except AuthenticationError:
            logger.error("Authentication failed.")
            raise EmbeddingError("Authentication failed. Please check your API key.")
        except APIError as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise EmbeddingError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            logger.exception("Unexpected error during embedding generation.")
            raise EmbeddingError(
                f"Unexpected error during embedding generation: {str(e)}"
            )
