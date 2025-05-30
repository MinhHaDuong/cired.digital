"""Unit tests for the download module."""

import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from intake.download import (
    download_pdf,
    get_pdf_filename,
    main,
    sanitize_filename,
)


def test_sanitize_filename_normal():
    """Test sanitize_filename with normal text."""
    assert sanitize_filename("normal_filename") == "normal_filename"


def test_sanitize_filename_with_special_chars():
    """Test sanitize_filename with special characters."""
    assert sanitize_filename("file/with:special*chars?") == "file_with_special_chars_"


def test_sanitize_filename_with_spaces():
    """Test sanitize_filename with spaces."""
    assert sanitize_filename("  file with spaces  ") == "file with spaces"


def test_sanitize_filename_empty():
    """Test sanitize_filename with empty string."""
    assert sanitize_filename("") == ""


def test_get_pdf_filename_with_halid():
    """Test get_pdf_filename with an entry containing halId_s."""
    entry = {"halId_s": "hal-12345"}
    with patch("src.intake.download.PDF_DIR", Path("/test/dir")):
        result = get_pdf_filename(entry)
        assert result == Path("/test/dir/hal-12345.pdf")


def test_get_pdf_filename_without_halid():
    """Test get_pdf_filename with an entry without halId_s."""
    entry = {"pdf_url": "http://example.com/paper.pdf"}
    expected_hash = hashlib.md5(entry["pdf_url"].encode()).hexdigest()

    with patch("src.intake.download.PDF_DIR", Path("/test/dir")):
        result = get_pdf_filename(entry)
        assert result == Path(f"/test/dir/{expected_hash}.pdf")


@pytest.fixture
def mock_response():
    """Create a mock response for requests.get."""
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.iter_content.return_value = [b"test", b"content"]
    return mock


def test_download_pdf_success(mock_response):
    """Test successful PDF download."""
    url = "http://example.com/paper.pdf"
    target_path = Path("/test/dir/paper.pdf")

    with patch("src.intake.download.requests.get", return_value=mock_response) as mock_get, \
         patch("builtins.open", mock_open()) as mock_file, \
         patch("src.intake.download.logging") as mock_logging, \
         patch.object(Path, "rename") as mock_rename, \
         patch.object(Path, "with_suffix", return_value=Path("/test/dir/paper.tmp")):

        result = download_pdf(url, target_path)

        mock_get.assert_called_once_with(url, stream=True, timeout=60)
        mock_file.assert_called_once_with(Path("/test/dir/paper.tmp"), "wb")
        mock_rename.assert_called_once()
        mock_logging.info.assert_called_once()
        assert result is True


def test_download_pdf_request_error():
    """Test PDF download with request error."""
    url = "http://example.com/paper.pdf"
    target_path = Path("/test/dir/paper.pdf")

    with patch("src.intake.download.requests.get", side_effect=requests.exceptions.RequestException("Error")), \
         patch("src.intake.download.logging") as mock_logging, \
         patch.object(Path, "exists", return_value=False), \
         patch.object(Path, "with_suffix", return_value=Path("/test/dir/paper.tmp")):

        result = download_pdf(url, target_path)

        mock_logging.warning.assert_called_once()
        assert result is False


def test_download_pdf_file_error(mock_response):
    """Test PDF download with file writing error."""
    url = "http://example.com/paper.pdf"
    target_path = Path("/test/dir/paper.pdf")

    with patch("src.intake.download.requests.get", return_value=mock_response), \
         patch("builtins.open", side_effect=OSError("File error")), \
         patch("src.intake.download.logging") as mock_logging, \
         patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "unlink") as mock_unlink, \
         patch.object(Path, "with_suffix", return_value=Path("/test/dir/paper.tmp")):

        result = download_pdf(url, target_path)

        mock_logging.warning.assert_called_once()
        mock_unlink.assert_called_once()
        assert result is False


def test_main_missing_publications_file():
    """Test main function when publications file is missing."""
    with patch("src.intake.download.PUBLICATIONS_FILE"), \
         patch("src.intake.download.logging") as mock_logging, \
         patch.object(Path, "exists", return_value=False):

        main()

        mock_logging.error.assert_called_once()


def test_main_with_publications():
    """Test main function with publications data."""
    publications = [
        {"pdf_url": "http://example.com/1.pdf", "halId_s": "hal-1"},
        {"pdf_url": "http://example.com/2.pdf"},
        {"title": "No PDF URL"}
    ]

    with patch("src.intake.download.PUBLICATIONS_FILE"), \
         patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "read_text", return_value=json.dumps(publications)), \
         patch("src.intake.download.get_pdf_filename") as mock_get_filename, \
         patch("src.intake.download.download_pdf", return_value=True) as mock_download, \
         patch("src.intake.download.logging"), \
         patch("src.intake.download.time.sleep"):

        mock_get_filename.side_effect = [Path("/test/1.pdf"), Path("/test/2.pdf")]

        with patch.object(Path, "exists", side_effect=[True, False]):
            main()

            assert mock_download.call_count == 1
