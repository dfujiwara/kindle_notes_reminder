"""
LLM response evaluation service using composition pattern.

This module provides evaluation services that can work with any LLMClientInterface
implementation. It uses composition rather than inheritance to separate evaluation
logic from LLM client implementations.

Includes utilities for parsing evaluation responses and validating scores.
"""

import logging
from sqlmodel import Session
from src.database import engine
from src.llm_interface import LLMClientInterface, LLMError, LLMPromptResponse
from src.prompts import create_evaluation_prompt, SYSTEM_INSTRUCTIONS
from src.repositories.evaluation_repository import EvaluationRepository
from src.repositories.interfaces import EvaluationRepositoryInterface
from src.repositories.models import Evaluation, NoteRead


logger = logging.getLogger(__name__)


class EvaluationError(Exception):
    """Base exception class for all evaluation-related errors"""

    pass


def _parse_evaluation_response(eval_content: str) -> tuple[float, str]:
    """
    Parse an LLM evaluation response to extract score and evaluation text.

    Expected format:
    Score: [0.0-1.0]
    Evaluation: [evaluation text]

    Args:
        eval_content: The raw evaluation response content from the LLM

    Returns:
        A tuple containing (score, evaluation_text) where:
        - score: A float between 0.0 and 1.0 representing quality
        - evaluation_text: A string describing the evaluation rationale

    Raises:
        EvaluationError: If the response format is invalid or required fields are missing

    Examples:
        >>> content = "Score: 0.8\\nEvaluation: Good response with clear explanations"
        >>> score, text = parse_evaluation_response(content)
        >>> score
        0.8
        >>> text
        'Good response with clear explanations'
    """
    if not eval_content or not eval_content.strip():
        logger.error("Empty evaluation response")
        raise EvaluationError("Empty evaluation response")

    # Parse the response to extract score and evaluation
    lines = eval_content.strip().split("\n")
    score_line = next((line for line in lines if line.startswith("Score:")), None)
    eval_line = next((line for line in lines if line.startswith("Evaluation:")), None)

    # Score parsing - require valid score format
    if not score_line:
        logger.error("No 'Score:' line found in evaluation response")
        raise EvaluationError("Evaluation response missing required 'Score:' line")

    try:
        score_text = score_line.split(":", 1)[1].strip()
        score = float(score_text)
        score = max(0.0, min(1.0, score))  # Clamp between 0.0 and 1.0
    except (ValueError, IndexError) as e:
        logger.error(f"Failed to parse score from '{score_line}': {str(e)}")
        raise EvaluationError(
            f"Invalid score format in evaluation response: {score_line}"
        )

    # Evaluation text extraction - require valid evaluation format
    if not eval_line:
        logger.error("No 'Evaluation:' line found in evaluation response")
        raise EvaluationError("Evaluation response missing required 'Evaluation:' line")

    try:
        evaluation_text = eval_line.split(":", 1)[1].strip()
    except IndexError as e:
        logger.error(f"Failed to parse evaluation text from '{eval_line}': {str(e)}")
        raise EvaluationError(f"Invalid evaluation format in response: {eval_line}")

    return score, evaluation_text


async def evaluate_llm_response(
    llm_client: LLMClientInterface, original_prompt: str, response: str
) -> tuple[float, str]:
    """
    Evaluate the quality of an LLM response using another LLM as the evaluator.

    This function uses composition to evaluate responses from any LLM client
    by using the same or different LLM client as an evaluator.

    Args:
        llm_client: Any LLM client implementing LLMClientInterface
        original_prompt: The original prompt that was sent to generate the response
        response: The response that was generated and needs evaluation

    Returns:
        A tuple containing (score, evaluation_text) where:
        - score: A float between 0.0 and 1.0 representing quality (1.0 = highest quality)
        - evaluation_text: A string describing the evaluation rationale

    Raises:
        EvaluationError: If there is an error during evaluation or response parsing

    Examples:
        >>> from src.openai_client import OpenAIClient
        >>> client = OpenAIClient()
        >>> score, text = await evaluate_llm_response(
        ...     client,
        ...     "What is Python?",
        ...     "Python is a programming language"
        ... )
        >>> score
        0.8
        >>> text
        'Good response but could be more detailed'
    """
    # Create evaluation prompt using the centralized prompt template
    evaluation_prompt = create_evaluation_prompt(original_prompt, response)

    # Use the LLM client to evaluate the response
    try:
        evaluation_response = await llm_client.get_response(
            evaluation_prompt, SYSTEM_INSTRUCTIONS["evaluator"]
        )
    except LLMError as e:
        logger.error(f"LLM client error during evaluation: {str(e)}")
        raise EvaluationError(f"Failed to get evaluation from LLM: {str(e)}")

    # Parse the evaluation response to extract score and text
    return _parse_evaluation_response(evaluation_response)


async def evaluate_response(
    llm_client: LLMClientInterface,
    llmInteraction: LLMPromptResponse,
    repository: EvaluationRepositoryInterface,
    note: NoteRead,
):
    result = await evaluate_llm_response(
        llm_client, llmInteraction.prompt, llmInteraction.response
    )
    evaluation = Evaluation(
        prompt=llmInteraction.prompt,
        response=llmInteraction.response,
        score=result[0],
        analysis=result[1],
        note_id=note.id,
    )
    repository.add(evaluation)


async def evaluate_response_background(
    llm_client: LLMClientInterface,
    llmInteraction: LLMPromptResponse,
    note: NoteRead,
) -> None:
    with Session(engine) as session:
        repository = EvaluationRepository(session)
        await evaluate_response(llm_client, llmInteraction, repository, note)
        session.commit()
