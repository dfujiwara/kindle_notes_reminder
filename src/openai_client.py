# src/openai_client.py
import openai
import os
from openai import APIError, RateLimitError, AuthenticationError
from llm_interface import LLMClientInterface, LLMError


class OpenAIClient(LLMClientInterface):
    def __init__(self, model:str ="gpt-3.5-turbo"):
        self.model = model
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def get_response(self, prompt: str) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            message_content = response.choices[0].message.content
            if message_content is None:
                raise LLMError("No response from OpenAI")
            return message_content.strip()
        except RateLimitError:
            raise LLMError("Rate limit exceeded. Please try again later.")
        except AuthenticationError:
            raise LLMError("Authentication failed. Please check your API key.")
        except APIError as e:
            raise LLMError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            # Catch unexpected errors and wrap them
            raise LLMError(f"Unexpected error during API call: {str(e)}")
