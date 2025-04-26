# src/openai_client.py
import openai
import os
import logging
from openai import APIError, RateLimitError, AuthenticationError
from src.llm_interface import LLMClientInterface, LLMError

# Configure logging
logger = logging.getLogger(__name__)

class OpenAIClient(LLMClientInterface):
    def __init__(self, model:str ="gpt-4o-mini"):
        self.model = model
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def get_response(self, prompt: str, instruction: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": prompt}
                ]
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
