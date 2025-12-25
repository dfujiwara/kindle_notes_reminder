"""Tests for content chunking functionality."""

from src.url_ingestion.content_chunker import chunk_text_by_paragraphs


def test_chunk_text_empty_string():
    """Test chunking empty string returns empty list."""
    result = chunk_text_by_paragraphs("")
    assert result == []


def test_chunk_text_whitespace_only():
    """Test chunking whitespace-only string returns empty list."""
    result = chunk_text_by_paragraphs("   \n\n   \n  ")
    assert result == []


def test_chunk_text_single_small_paragraph():
    """Test chunking single paragraph under max size."""
    text = "This is a short paragraph."
    result = chunk_text_by_paragraphs(text, max_chunk_size=1000)

    assert len(result) == 1
    assert result[0].content == text
    assert result[0].chunk_order == 0
    assert len(result[0].content_hash) == 64  # SHA-256 hash length


def test_chunk_text_multiple_small_paragraphs():
    """Test chunking multiple small paragraphs combined into one chunk."""
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    result = chunk_text_by_paragraphs(text, max_chunk_size=1000)

    assert len(result) == 1
    assert "Paragraph one." in result[0].content
    assert "Paragraph two." in result[0].content
    assert "Paragraph three." in result[0].content
    assert result[0].chunk_order == 0
    # Check that double newlines are preserved
    assert "\n\n" in result[0].content


def test_chunk_text_paragraphs_split_at_max_size():
    """Test that paragraphs are split when combined size exceeds max."""
    text = "A" * 600 + "\n\n" + "B" * 600
    result = chunk_text_by_paragraphs(text, max_chunk_size=1000)

    assert len(result) == 2
    assert result[0].content == "A" * 600
    assert result[0].chunk_order == 0
    assert result[1].content == "B" * 600
    assert result[1].chunk_order == 1


def test_chunk_text_combines_small_paragraphs():
    """Test that small paragraphs are combined up to max size."""
    para1 = "A" * 300
    para2 = "B" * 300
    para3 = "C" * 300
    para4 = "D" * 300
    text = f"{para1}\n\n{para2}\n\n{para3}\n\n{para4}"

    result = chunk_text_by_paragraphs(text, max_chunk_size=1000)

    # Should combine into 2 chunks (300+300+300 = 900 fits, then 300 alone)
    assert len(result) == 2
    assert para1 in result[0].content
    assert para2 in result[0].content
    assert para3 in result[0].content
    assert result[1].content == para4


def test_chunk_text_with_sentence_splitting():
    """Test that large paragraphs are split on sentence boundaries."""
    # Create a paragraph with multiple sentences that exceeds max size
    sentence1 = "A" * 600 + "."
    sentence2 = "B" * 600 + "."
    paragraph = sentence1 + " " + sentence2

    result = chunk_text_by_paragraphs(paragraph, max_chunk_size=1000)

    # Should split into 2 chunks at sentence boundary
    assert len(result) == 2
    assert "A" * 600 in result[0].content
    assert "B" * 600 in result[1].content


def test_chunk_text_strips_whitespace():
    """Test that whitespace is properly handled."""
    text = "  Paragraph one.  \n\n  Paragraph two.  "
    result = chunk_text_by_paragraphs(text, max_chunk_size=1000)

    assert len(result) == 1
    assert result[0].content == "Paragraph one.\n\nParagraph two."


def test_chunk_text_custom_max_size():
    """Test chunking with custom max size."""
    text = "A" * 50 + "\n\n" + "B" * 50

    # With small max size, should split
    result_small = chunk_text_by_paragraphs(text, max_chunk_size=60)
    assert len(result_small) == 2

    # With large max size, should combine
    result_large = chunk_text_by_paragraphs(text, max_chunk_size=200)
    assert len(result_large) == 1


def test_chunk_text_preserves_all_content():
    """Test that all original content is preserved across chunks."""
    text = (
        "First paragraph with content.\n\n"
        "Second paragraph with different content.\n\n"
        "Third paragraph with even more content."
    )

    result = chunk_text_by_paragraphs(text, max_chunk_size=50)

    # Reconstruct original text from chunks (accounting for paragraph boundaries)
    reconstructed = "\n\n".join(chunk.content for chunk in result)
    assert text == reconstructed


def test_chunk_text_real_world_example():
    """Test with realistic article content."""
    text = """Web scraping is a technique for extracting data from websites. It involves making HTTP requests to web pages and parsing the HTML content to extract the desired information.

There are several tools available for web scraping in Python. BeautifulSoup is popular for parsing HTML, while requests or httpx are used for making HTTP requests.

When scraping websites, it's important to respect robots.txt files and implement rate limiting. Always check the website's terms of service before scraping."""

    result = chunk_text_by_paragraphs(text, max_chunk_size=200)

    # Should create 3 chunks (one per paragraph)
    assert len(result) == 3
    assert result[0].chunk_order == 0
    assert result[1].chunk_order == 1
    assert result[2].chunk_order == 2
    assert "Web scraping" in result[0].content
    assert "BeautifulSoup" in result[1].content
    assert "robots.txt" in result[2].content


def test_chunk_text_very_long_single_sentence():
    """Test handling of a single very long sentence."""
    # Single sentence with no punctuation that exceeds max size
    text = "A" * 3000

    result = chunk_text_by_paragraphs(text, max_chunk_size=1000)

    assert len(result) == 3
    assert all(len(chunk.content) <= 1000 for chunk in result)
    # Verify all content preserved
    combined = "".join(chunk.content for chunk in result)
    assert combined == text


def test_chunk_text_mixed_paragraph_sizes():
    """Test with mix of small, medium, and large paragraphs."""
    small = "Small."
    medium = "M" * 500
    large = "L" * 1500

    text = f"{small}\n\n{medium}\n\n{large}"

    result = chunk_text_by_paragraphs(text, max_chunk_size=1000)

    # small + medium should combine (< 1000)
    # large should split into 2 chunks
    assert len(result) == 3
    assert small in result[0].content
    assert "M" * 500 in result[0].content
    assert "L" in result[1].content
    assert "L" in result[2].content
