"""Unit tests for the verify module."""

import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from intake.verify import (
    check_r2r,
    describe_table,
    get_existing_documents,
    normalize_title,
    show_failed_ingestions,
    show_repeat_halid,
    show_repeat_titles,
    show_short_titles,
)


@pytest.fixture
def sample_documents_df():
    """Create a sample DataFrame of documents for testing."""
    data = {
        "id": ["doc1", "doc2", "doc3", "doc4"],
        "title": ["Test Document", "Another Test", None, "Test Document"],
        "size_in_bytes": [1000, 2000, 3000, 4000],
        "ingestion_status": ["success", "failed", "success", "success"],
        "extraction_status": ["success", "failed", "pending", "success"],
        "created_at": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"]),
        "updated_at": pd.to_datetime(["2023-01-01", "2023-01-02", "2023-01-03", "2023-01-04"]),
        "type": ["pdf", "pdf", "docx", "pdf"],
        "meta_title": ["Test Document", "Another Test", "Untitled", "Test Document"],
        "meta_hal_id": ["hal-1234", "hal-5678", None, "hal-1234"],
        "meta_source_url": ["http://example.com/1", "http://example.com/2", None, "http://example.com/4"],
        "meta_citation": ["Citation 1", "Citation 2", None, "Citation 4"]
    }
    return pd.DataFrame(data)


def test_check_r2r_success():
    """Test check_r2r with successful connection."""
    mock_client = MagicMock()

    with patch("src.intake.verify.logging") as mock_logging:
        result = check_r2r(mock_client)

        assert result is True
        mock_client.documents.list.assert_called_once_with(limit=1)
        mock_logging.debug.assert_called_once()


def test_check_r2r_failure():
    """Test check_r2r with failed connection."""
    mock_client = MagicMock()
    mock_client.documents.list.side_effect = Exception("Connection error")

    with patch("src.intake.verify.logging") as mock_logging:
        result = check_r2r(mock_client)

        assert result is False
        mock_logging.warning.assert_called_once()


def test_get_existing_documents_success():
    """Test successful retrieval of documents."""
    mock_client = MagicMock()
    mock_client.documents.export.return_value = None  # Just to indicate success

    mock_df = pd.DataFrame({
        "id": ["doc1", "doc2"],
        "title": ["Test 1", "Test 2"],
        "metadata": ['{"key1": "value1"}', '{"key2": "value2"}']
    })

    with patch("src.intake.verify.pd.read_csv", return_value=mock_df), \
         patch("src.intake.verify.pd.json_normalize", return_value=pd.DataFrame({"meta_key1": ["value1"], "meta_key2": ["value2"]})), \
         patch("src.intake.verify.logging") as mock_logging:

        result = get_existing_documents(mock_client)

        assert result is not None
        assert len(result) == 2
        mock_client.documents.export.assert_called_once()
        mock_logging.info.assert_called_once()


def test_get_existing_documents_error():
    """Test error handling in get_existing_documents."""
    mock_client = MagicMock()
    mock_client.documents.export.side_effect = Exception("Export error")

    with patch("src.intake.verify.logging") as mock_logging:
        result = get_existing_documents(mock_client)

        assert result is None
        mock_logging.error.assert_called_once()


def test_describe_table(sample_documents_df):
    """Test describe_table function."""
    with patch("builtins.print") as mock_print:
        describe_table(sample_documents_df)

        assert mock_print.call_count > 0


def test_show_short_titles_with_anomalies(sample_documents_df):
    """Test show_short_titles with anomalous titles."""
    with patch("builtins.print") as mock_print:
        result = show_short_titles(sample_documents_df)

        assert result == 1  # One null title
        assert mock_print.call_count > 0


def test_show_short_titles_missing_columns():
    """Test show_short_titles with missing columns."""
    df = pd.DataFrame({"id": ["doc1"]})  # Missing title column

    with patch("builtins.print") as mock_print:
        result = show_short_titles(df)

        assert result > 0  # Should return an error code
        assert mock_print.call_count > 0


def test_show_failed_ingestions_with_failures(sample_documents_df):
    """Test show_failed_ingestions with failed ingestions."""
    with patch("builtins.print") as mock_print:
        result = show_failed_ingestions(sample_documents_df)

        assert result == 1  # One failed ingestion
        assert mock_print.call_count > 0


def test_show_failed_ingestions_no_failures():
    """Test show_failed_ingestions with no failures."""
    df = pd.DataFrame({
        "id": ["doc1", "doc2"],
        "ingestion_status": ["success", "success"]
    })

    with patch("builtins.print") as mock_print:
        result = show_failed_ingestions(df)

        assert result == 0  # No failures
        assert mock_print.call_count > 0


def test_show_failed_ingestions_missing_column():
    """Test show_failed_ingestions with missing ingestion_status column."""
    df = pd.DataFrame({"id": ["doc1"]})  # Missing ingestion_status column

    with patch("builtins.print") as mock_print:
        result = show_failed_ingestions(df)

        assert result == 0  # Should return 0 (no failures found)
        assert mock_print.call_count > 0


def test_show_repeat_halid_with_duplicates(sample_documents_df):
    """Test show_repeat_halid with duplicate HAL IDs."""
    with patch("builtins.print") as mock_print:
        result = show_repeat_halid(sample_documents_df)

        assert result == 2  # Two documents with the same HAL ID
        assert mock_print.call_count > 0


def test_show_repeat_halid_no_duplicates():
    """Test show_repeat_halid with no duplicate HAL IDs."""
    df = pd.DataFrame({
        "id": ["doc1", "doc2"],
        "meta_hal_id": ["hal-1234", "hal-5678"]
    })

    with patch("builtins.print") as mock_print:
        result = show_repeat_halid(df)

        assert result == 0  # No duplicates
        assert mock_print.call_count > 0


def test_show_repeat_halid_missing_column():
    """Test show_repeat_halid with missing meta_hal_id column."""
    df = pd.DataFrame({"id": ["doc1"]})  # Missing meta_hal_id column

    with patch("builtins.print") as mock_print:
        result = show_repeat_halid(df)

        assert result == 0  # Should return 0 (no duplicates found)
        assert mock_print.call_count > 0


def test_normalize_title():
    """Test normalize_title function."""
    assert normalize_title("Test Document") == "test document"
    assert normalize_title("Test, Document!") == "test document"
    assert normalize_title("  Test   Document  ") == "test document"


def test_show_repeat_titles_with_duplicates(sample_documents_df):
    """Test show_repeat_titles with duplicate titles."""
    with patch("builtins.print") as mock_print:
        result = show_repeat_titles(sample_documents_df)

        assert result == 2  # Two documents with the same normalized title
        assert mock_print.call_count > 0


def test_show_repeat_titles_no_duplicates():
    """Test show_repeat_titles with no duplicate titles."""
    df = pd.DataFrame({
        "id": ["doc1", "doc2"],
        "title": ["Test Document 1", "Test Document 2"]
    })

    with patch("builtins.print") as mock_print:
        result = show_repeat_titles(df)

        assert result == 0  # No duplicates
        assert mock_print.call_count > 0


def test_show_repeat_titles_missing_column():
    """Test show_repeat_titles with missing title column."""
    df = pd.DataFrame({"id": ["doc1"]})  # Missing title column

    with patch("builtins.print") as mock_print:
        result = show_repeat_titles(df)

        assert result == 0  # Should return 0 (no duplicates found)
        assert mock_print.call_count > 0
