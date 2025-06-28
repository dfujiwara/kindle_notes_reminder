"""
Tests for the evaluations module.

Tests public evaluation functions and error handling through the public API.
"""

import pytest
from .evaluations import (
    evaluate_llm_response,
    EvaluationError,
)
from .test_utils import StubLLMClient


@pytest.mark.asyncio
async def test_evaluate_llm_response_success():
    """Test successful LLM response evaluation."""
    # Mock LLM response in correct format
    mock_response = "Score: 0.85\nEvaluation: Well-structured and informative response."
    llm_client = StubLLMClient(response=mock_response)

    score, evaluation = await evaluate_llm_response(
        llm_client, "What is Python?", "Python is a programming language."
    )

    assert score == 0.85
    assert evaluation == "Well-structured and informative response."


@pytest.mark.asyncio
async def test_evaluate_llm_response_llm_client_error():
    """Test evaluation when LLM client fails."""
    llm_client = StubLLMClient(should_fail=True)

    with pytest.raises(EvaluationError, match="Failed to get evaluation from LLM"):
        await evaluate_llm_response(llm_client, "Test prompt", "Test response")


@pytest.mark.asyncio
async def test_evaluate_llm_response_invalid_response_format():
    """Test evaluation with invalid LLM response format."""
    # LLM returns response in wrong format
    mock_response = "This is not a properly formatted evaluation response."
    llm_client = StubLLMClient(response=mock_response)

    with pytest.raises(EvaluationError, match="missing required 'Score:' line"):
        await evaluate_llm_response(llm_client, "Test prompt", "Test response")


@pytest.mark.asyncio
async def test_evaluate_llm_response_score_clamping():
    """Test that scores are properly clamped to [0.0, 1.0] range."""
    # Test score above 1.0
    mock_response = "Score: 1.5\nEvaluation: Excellent response"
    llm_client = StubLLMClient(response=mock_response)

    score, evaluation = await evaluate_llm_response(
        llm_client, "Test prompt", "Test response"
    )

    assert score == 1.0  # Clamped to maximum
    assert evaluation == "Excellent response"

    # Test negative score
    mock_response = "Score: -0.2\nEvaluation: Poor response"
    llm_client = StubLLMClient(response=mock_response)

    score, evaluation = await evaluate_llm_response(
        llm_client, "Test prompt", "Test response"
    )

    assert score == 0.0  # Clamped to minimum
    assert evaluation == "Poor response"


@pytest.mark.asyncio
async def test_evaluate_llm_response_with_extra_content():
    """Test evaluation handles extra content in response."""
    mock_response = """Some extra text at the beginning
Score: 0.75
More text in between
Evaluation: The response addresses the question adequately.
Some trailing text"""

    llm_client = StubLLMClient(response=mock_response)

    score, evaluation = await evaluate_llm_response(
        llm_client, "Test prompt", "Test response"
    )

    assert score == 0.75
    assert evaluation == "The response addresses the question adequately."


@pytest.mark.asyncio
async def test_evaluate_llm_response_missing_evaluation_field():
    """Test evaluation with missing Evaluation field."""
    mock_response = "Score: 0.8"
    llm_client = StubLLMClient(response=mock_response)

    with pytest.raises(EvaluationError, match="missing required 'Evaluation:' line"):
        await evaluate_llm_response(llm_client, "Test prompt", "Test response")


@pytest.mark.asyncio
async def test_evaluate_llm_response_invalid_score_format():
    """Test evaluation with invalid score format."""
    mock_response = "Score: not_a_number\nEvaluation: Test evaluation"
    llm_client = StubLLMClient(response=mock_response)

    with pytest.raises(EvaluationError, match="Invalid score format"):
        await evaluate_llm_response(llm_client, "Test prompt", "Test response")


@pytest.mark.asyncio
async def test_evaluate_llm_response_calls_llm_with_correct_params():
    """Test that evaluation calls LLM with correct prompt and instruction."""
    mock_response = "Score: 0.7\nEvaluation: Good response."
    llm_client = StubLLMClient(response=mock_response)

    await evaluate_llm_response(llm_client, "Original prompt", "LLM response")
    assert llm_client.call_count == 1
