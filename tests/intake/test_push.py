"""Unit tests for the push module."""

import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from intake.push import (
    check_r2r_connection,
    exclude_oversized_pdfs,
    first_if_list,
    format_metadata_for_upload,
    get_args,
    get_existing_documents,
    load_metadata,
    prepare_pdf_files,
    upload_pdfs,
)


def test_get_args_defaults():
    """Test get_args with default values."""
    with patch("src.intake.push.argparse.ArgumentParser.parse_args") as mock_parse:
        mock_parse.return_value = MagicMock(
            dir=Path("/test/dir"),
            recursive=False,
            base_url="http://localhost:7272",
            collection=None,
            max_upload=5,
            metadata_file=Path("/test/metadata.json"),
            no_metadata=False,
            verbose=False
        )

        args = get_args()

        assert args.dir == Path("/test/dir")
        assert args.recursive is False
        assert args.base_url == "http://localhost:7272"
        assert args.collection is None
        assert args.max_upload == 5
        assert args.metadata_file == Path("/test/metadata.json")
        assert args.no_metadata is False
        assert args.verbose is False


def test_prepare_pdf_files_directory_not_found():
    """Test prepare_pdf_files when directory doesn't exist."""
    args = MagicMock(dir=Path("/nonexistent"), recursive=False)

    with patch.object(Path, "is_dir", return_value=False), \
         patch("src.intake.push.logging") as mock_logging:

        result = prepare_pdf_files(args)

        assert result == []
        mock_logging.error.assert_called_once()


def test_prepare_pdf_files_no_pdfs():
    """Test prepare_pdf_files when no PDFs are found."""
    args = MagicMock(dir=Path("/test/dir"), recursive=False, max_upload=5)

    with patch.object(Path, "is_dir", return_value=True), \
         patch.object(Path, "glob", return_value=[]), \
         patch("src.intake.push.logging") as mock_logging:

        result = prepare_pdf_files(args)

        assert result == []
        mock_logging.warning.assert_called_once()


def test_prepare_pdf_files_with_pdfs():
    """Test prepare_pdf_files with PDFs found."""
    args = MagicMock(dir=Path("/test/dir"), recursive=False, max_upload=5)
    pdf_files = [Path("/test/dir/file1.pdf"), Path("/test/dir/file2.pdf")]

    with patch.object(Path, "is_dir", return_value=True), \
         patch.object(Path, "glob", return_value=pdf_files), \
         patch("src.intake.push.logging") as mock_logging:

        result = prepare_pdf_files(args)

        assert result == pdf_files
        assert mock_logging.info.call_count == 2


def test_prepare_pdf_files_recursive():
    """Test prepare_pdf_files with recursive option."""
    args = MagicMock(dir=Path("/test/dir"), recursive=True, max_upload=5)

    with patch.object(Path, "is_dir", return_value=True), \
         patch.object(Path, "glob", return_value=[]), \
         patch("src.intake.push.logging"):

        prepare_pdf_files(args)

        Path.glob.assert_called_once_with("**/*.pdf")


def test_exclude_oversized_pdfs():
    """Test excluding oversized PDFs."""
    pdf_files = [
        Path("/test/dir/small.pdf"),
        Path("/test/dir/large.pdf"),
        Path("/test/dir/medium.pdf")
    ]

    def mock_stat(path):
        if "large" in str(path):
            return MagicMock(st_size=31_000_000)  # Over the limit
        return MagicMock(st_size=1_000_000)  # Under the limit

    with patch.object(Path, "stat", side_effect=mock_stat), \
         patch("src.intake.push.MAX_FILE_SIZE", 30_000_000), \
         patch("src.intake.push.logging") as mock_logging:

        result = exclude_oversized_pdfs(pdf_files)

        assert len(result) == 2
        assert Path("/test/dir/large.pdf") not in result
        assert Path("/test/dir/small.pdf") in result
        assert Path("/test/dir/medium.pdf") in result
        mock_logging.warning.assert_called_once()
        mock_logging.info.assert_called_once()


def test_get_existing_documents():
    """Test fetching existing documents."""
    mock_client = MagicMock()
    mock_doc1 = MagicMock(title="Doc1", ingestion_status="success")
    mock_doc2 = MagicMock(title="Doc2", ingestion_status="failed")

    mock_client.documents.list.side_effect = [
        MagicMock(results=[mock_doc1, mock_doc2]),
        MagicMock(results=[])
    ]

    with patch("src.intake.push.logging"):
        result = get_existing_documents(mock_client)

        assert len(result) == 2
        assert result["Doc1"] == "success"
        assert result["Doc2"] == "failed"
        assert mock_client.documents.list.call_count == 2


def test_get_existing_documents_error():
    """Test error handling in get_existing_documents."""
    mock_client = MagicMock()
    mock_client.documents.list.side_effect = Exception("API error")

    with patch("src.intake.push.logging") as mock_logging:
        result = get_existing_documents(mock_client)

        assert result == {}
        mock_logging.error.assert_called_once()


def test_load_metadata_file_not_found():
    """Test load_metadata when file doesn't exist."""
    with patch.object(Path, "exists", return_value=False), \
         patch("src.intake.push.logging") as mock_logging:

        result = load_metadata(Path("/nonexistent.json"))

        assert result == {}
        mock_logging.warning.assert_called_once()


def test_load_metadata_with_valid_file():
    """Test load_metadata with a valid JSON file."""
    publications = [
        {"halId_s": "hal-12345", "title": "Test Paper 1"},
        {"pdf_url": "http://example.com/paper.pdf", "title": "Test Paper 2"},
        {"title": "Test Paper 3"}  # No halId_s or pdf_url
    ]

    with patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "read_text", return_value=json.dumps(publications)), \
         patch("src.intake.push.logging"):

        result = load_metadata(Path("/test/metadata.json"))

        assert "hal-12345" in result
        assert "hal_12345" in result  # Also creates underscore version

        hash_key = hashlib.md5(b"http://example.com/paper.pdf").hexdigest()
        assert hash_key in result

        assert len(result) == 3  # 2 keys for halId_s + 1 for pdf_url


def test_load_metadata_invalid_json():
    """Test load_metadata with invalid JSON."""
    with patch.object(Path, "exists", return_value=True), \
         patch.object(Path, "read_text", return_value="invalid json"), \
         patch("src.intake.push.logging") as mock_logging:

        result = load_metadata(Path("/test/metadata.json"))

        assert result == {}
        mock_logging.error.assert_called_once()


def test_first_if_list_with_list():
    """Test first_if_list with a list input."""
    assert first_if_list(["item1", "item2"]) == "item1"


def test_first_if_list_with_string():
    """Test first_if_list with a string input."""
    assert first_if_list("single_item") == "single_item"


def test_first_if_list_with_empty_list():
    """Test first_if_list with an empty list."""
    assert first_if_list([]) is None


def test_first_if_list_with_none():
    """Test first_if_list with None input."""
    assert first_if_list(None) is None


def test_format_metadata_for_upload():
    """Test formatting metadata for upload."""
    hal_metadata = {
        "title_s": "Test Title",
        "label_s": "Test Citation",
        "abstract_s": "Test Abstract",
        "authFullName_s": ["Author 1", "Author 2"],
        "producedDate_tdate": "2023-01-01",
        "doiId_s": "10.1234/test",
        "halId_s": "hal-12345",
        "docType_s": "ART"
    }

    result = format_metadata_for_upload(hal_metadata)

    assert result["title"] == "Test Title"
    assert result["citation"] == "Test Citation"
    assert result["description"] == "Test Abstract"
    assert result["authors"] == ["Author 1", "Author 2"]
    assert result["publication_date"] == "2023-01-01"
    assert result["doi"] == "10.1234/test"
    assert result["source_url"] == "https://doi.org/10.1234/test"
    assert result["hal_id"] == "hal-12345"
    assert result["document_type"] == "ART"


def test_format_metadata_for_upload_single_author():
    """Test formatting metadata with a single author (string instead of list)."""
    hal_metadata = {
        "title_s": "Test Title",
        "authFullName_s": "Single Author"
    }

    result = format_metadata_for_upload(hal_metadata)

    assert result["authors"] == ["Single Author"]


def test_format_metadata_for_upload_hal_url():
    """Test formatting metadata with HAL ID but no DOI."""
    hal_metadata = {
        "halId_s": "hal-12345"
    }

    result = format_metadata_for_upload(hal_metadata)

    assert result["source_url"] == "https://hal.science/hal-12345"


def test_upload_pdfs_success():
    """Test successful PDF upload."""
    pdf_files = [Path("/test/file1.pdf"), Path("/test/file2.pdf")]
    client = MagicMock()
    existing_documents = {}
    metadata_by_file = {
        "file1": {"title_s": "Test Title 1"},
        "file2": {"title_s": "Test Title 2"}
    }

    with patch("src.intake.push.format_metadata_for_upload") as mock_format, \
         patch("src.intake.push.logging"):

        mock_format.side_effect = [
            {"title": "Test Title 1"},
            {"title": "Test Title 2"}
        ]

        success, skipped, failed = upload_pdfs(
            pdf_files, client, existing_documents, metadata_by_file
        )

        assert success == 2
        assert skipped == 0
        assert len(failed) == 0
        assert client.documents.create.call_count == 2


def test_upload_pdfs_skip_existing():
    """Test skipping already ingested PDFs."""
    pdf_files = [Path("/test/file1.pdf"), Path("/test/file2.pdf")]
    client = MagicMock()
    existing_documents = {"Test Title 1": "success"}
    metadata_by_file = {
        "file1": {"title_s": "Test Title 1"},
        "file2": {"title_s": "Test Title 2"}
    }

    with patch("src.intake.push.format_metadata_for_upload") as mock_format, \
         patch("src.intake.push.logging"):

        mock_format.side_effect = [
            {"title": "Test Title 1"},
            {"title": "Test Title 2"}
        ]

        success, skipped, failed = upload_pdfs(
            pdf_files, client, existing_documents, metadata_by_file
        )

        assert success == 1
        assert skipped == 1
        assert len(failed) == 0
        assert client.documents.create.call_count == 1


def test_upload_pdfs_retry_failed():
    """Test retrying PDFs with failed ingestion status."""
    pdf_files = [Path("/test/file1.pdf")]
    client = MagicMock()
    existing_documents = {"Test Title 1": "failed"}
    metadata_by_file = {
        "file1": {"title_s": "Test Title 1"}
    }

    with patch("src.intake.push.format_metadata_for_upload") as mock_format, \
         patch("src.intake.push.logging"):

        mock_format.return_value = {"title": "Test Title 1"}

        success, skipped, failed = upload_pdfs(
            pdf_files, client, existing_documents, metadata_by_file
        )

        assert success == 1
        assert skipped == 0
        assert len(failed) == 0
        assert client.documents.create.call_count == 1


def test_upload_pdfs_with_error():
    """Test handling upload errors."""
    pdf_files = [Path("/test/file1.pdf")]
    client = MagicMock()
    client.documents.create.side_effect = Exception("Upload error")
    existing_documents = {}
    metadata_by_file = {
        "file1": {"title_s": "Test Title 1"}
    }

    with patch("src.intake.push.format_metadata_for_upload"), \
         patch("src.intake.push.logging") as mock_logging:

        success, skipped, failed = upload_pdfs(
            pdf_files, client, existing_documents, metadata_by_file
        )

        assert success == 0
        assert skipped == 0
        assert len(failed) == 1
        assert failed[0][0] == Path("/test/file1.pdf")
        mock_logging.error.assert_called_once()


def test_upload_pdfs_max_upload_limit():
    """Test respecting max_upload limit."""
    pdf_files = [Path("/test/file1.pdf"), Path("/test/file2.pdf"), Path("/test/file3.pdf")]
    client = MagicMock()
    existing_documents = {}
    metadata_by_file = {}

    with patch("src.intake.push.logging"):
        success, skipped, failed = upload_pdfs(
            pdf_files, client, existing_documents, metadata_by_file, max_upload=2
        )

        assert success == 2
        assert client.documents.create.call_count == 2


def test_check_r2r_connection_success():
    """Test successful R2R connection check."""
    client = MagicMock()

    with patch("src.intake.push.logging"):
        result = check_r2r_connection(client)

        assert result is True
        client.documents.list.assert_called_once_with(limit=1)


def test_check_r2r_connection_failure():
    """Test failed R2R connection check."""
    client = MagicMock()
    client.documents.list.side_effect = Exception("Connection error")

    with patch("src.intake.push.logging") as mock_logging:
        result = check_r2r_connection(client)

        assert result is False
        mock_logging.error.assert_called_once()
