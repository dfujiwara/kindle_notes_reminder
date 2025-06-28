"""
Tests for the prompts module.

Tests core prompt template functions and system instructions.
"""

from .prompts import (
    create_evaluation_prompt,
    create_context_prompt,
)


def test_basic_evaluation_prompt():
    """Test basic evaluation prompt generation."""
    original_prompt = "What is Python?"
    llm_response = "Python is a programming language."

    prompt = create_evaluation_prompt(original_prompt, llm_response)

    assert original_prompt in prompt
    assert llm_response in prompt
    assert "Original Prompt:" in prompt
    assert "LLM Response:" in prompt


def test_evaluation_prompt_contains_criteria():
    """Test that evaluation prompt contains evaluation criteria."""
    prompt = create_evaluation_prompt("test prompt", "test response")

    # Should contain all evaluation criteria
    assert "Relevance:" in prompt
    assert "Accuracy:" in prompt
    assert "Helpfulness:" in prompt
    assert "Clarity:" in prompt


def test_evaluation_prompt_contains_format_instructions():
    """Test that evaluation prompt contains formatting instructions."""
    prompt = create_evaluation_prompt("test prompt", "test response")

    assert "Score:" in prompt
    assert "Evaluation:" in prompt
    assert "0.0 to 1.0" in prompt
    assert "Format your response as:" in prompt


def test_basic_context_prompt():
    """Test basic context prompt generation."""
    book_title = "Python Programming"
    note_content = "Variables store data"

    prompt = create_context_prompt(book_title, note_content)
    assert book_title in prompt
    assert note_content in prompt


def test_context_prompt_structure():
    """Test that context prompt has expected structure."""
    book_title = "Test Book"
    note_content = "Test note content"
    prompt = create_context_prompt(book_title, note_content)
    assert "notebook titled" in prompt
    assert "additional context" in prompt
    assert "insights" in prompt
