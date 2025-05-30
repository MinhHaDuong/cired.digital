"""Unit tests for the query module."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from intake.query import (
    get_paginated_publications,
    main,
    process_publications,
)


@pytest.fixture
def sample_publications():
    """Create sample publication data for testing."""
    return [
        {
            "label_s": "Publication with &amp; HTML entity",
            "producedDate_tdate": "2023-01-01T00:00:00Z",
            "fileMain_s": "http://example.com/pdf1.pdf",
            "labStructAcronym_s": "CIRED"
        },
        {
            "label_s": "CIRED Conference paper",
            "producedDate_tdate": "2023-02-01T00:00:00Z",
            "fileMain_s": "http://example.com/pdf2.pdf"
        },
        {
            "label_s": "Another CIRED lab paper",
            "labStructAcronym_s": "CIRED"
        }
    ]


def test_process_publications(sample_publications):
    """Test processing publications and separating them into related and unrelated."""
    with patch("src.intake.query.PUBLICATIONS_FILE"), \
         patch("src.intake.query.CONFERENCE_FILE"), \
         patch("src.intake.query.logging"), \
         patch.object(Path, "parent"), \
         patch.object(Path, "mkdir"), \
         patch.object(Path, "write_text") as mock_write:

        process_publications(sample_publications)

        assert mock_write.call_count == 2

        related_pubs_json = mock_write.call_args_list[0][0][0]
        related_pubs = json.loads(related_pubs_json)

        unrelated_pubs_json = mock_write.call_args_list[1][0][0]
        unrelated_pubs = json.loads(unrelated_pubs_json)

        assert len(related_pubs) == 2  # Publications with labStructAcronym_s = "CIRED"
        assert len(unrelated_pubs) == 1  # Publications with "CIRED" in label but no labStructAcronym_s

        assert related_pubs[0]["label_s"] == "Publication with & HTML entity"

        assert related_pubs[0]["producedDate_tdate"] == "2023-01-01"

        assert "pdf_url" in related_pubs[0]
        assert related_pubs[0]["pdf_url"] == "http://example.com/pdf1.pdf"


@pytest.fixture
def mock_hal_response():
    """Create a mock response for HAL API requests."""
    mock = MagicMock()
    mock.json.return_value = {
        "response": {
            "docs": [
                {"id": "doc1", "label_s": "Test Document 1"},
                {"id": "doc2", "label_s": "Test Document 2"}
            ]
        }
    }
    return mock


def test_get_paginated_publications_success(mock_hal_response):
    """Test successful retrieval of paginated publications."""
    params = {"q": "CIRED", "fl": "fields", "wt": "json"}

    with patch("src.intake.query.requests.get", return_value=mock_hal_response) as mock_get, \
         patch("src.intake.query.logging"), \
         patch("src.intake.query.time.sleep"):

        mock_get.side_effect = [
            mock_hal_response,
            MagicMock(json=lambda: {"response": {"docs": []}})
        ]

        result = get_paginated_publications(params)

        assert len(result) == 2
        assert result[0]["id"] == "doc1"
        assert result[1]["id"] == "doc2"
        assert mock_get.call_count == 2


def test_get_paginated_publications_timeout():
    """Test pagination with timeout error."""
    params = {"q": "CIRED", "fl": "fields", "wt": "json"}

    with patch("src.intake.query.requests.get", side_effect=requests.exceptions.Timeout("Timeout")), \
         patch("src.intake.query.logging") as mock_logging:

        result = get_paginated_publications(params)

        assert result == []
        mock_logging.error.assert_called_once()


def test_get_paginated_publications_http_error():
    """Test pagination with HTTP error."""
    params = {"q": "CIRED", "fl": "fields", "wt": "json"}

    with patch("src.intake.query.requests.get", side_effect=requests.exceptions.HTTPError("404")), \
         patch("src.intake.query.logging") as mock_logging:

        result = get_paginated_publications(params)

        assert result == []
        mock_logging.error.assert_called_once()


def test_main_success():
    """Test main function with successful API call."""
    mock_publications = [{"id": "doc1"}]

    with patch("src.intake.query.get_paginated_publications", return_value=mock_publications) as mock_get, \
         patch("src.intake.query.process_publications") as mock_process:

        main()

        mock_get.assert_called_once()
        mock_process.assert_called_once_with(mock_publications)


def test_main_no_publications():
    """Test main function with no publications returned."""
    with patch("src.intake.query.get_paginated_publications", return_value=[]) as mock_get, \
         patch("src.intake.query.process_publications") as mock_process, \
         patch("src.intake.query.logging") as mock_logging:

        main()

        mock_get.assert_called_once()
        mock_process.assert_not_called()
        mock_logging.warning.assert_called_once()
