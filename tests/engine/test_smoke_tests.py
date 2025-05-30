"""Unit tests for the engine smoke-tests modules."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from engine.smoke_tests.hello_r2r import main as hello_r2r_main


@pytest.fixture
def mock_r2r_client():
    """Create a mock R2R client."""
    mock_client = MagicMock()

    mock_rag_response = MagicMock()
    mock_rag_response.results.generated_answer = "Test answer"
    mock_client.retrieval.rag.return_value = mock_rag_response

    return mock_client


@pytest.fixture
def mock_r2r_utils():
    """Mock the r2r_test_utils module."""
    with patch("src.engine.smoke_tests.hello_r2r.write_test_file") as mock_write, \
         patch("src.engine.smoke_tests.hello_r2r.create_or_get_document", return_value="doc123"), \
         patch("src.engine.smoke_tests.hello_r2r.delete_document") as mock_delete_doc, \
         patch("src.engine.smoke_tests.hello_r2r.delete_test_file") as mock_delete_file, \
         patch("src.engine.smoke_tests.hello_r2r.client", MagicMock()) as mock_client:

        mock_client.retrieval.rag.return_value = MagicMock(
            results=MagicMock(generated_answer="Test RAG answer")
        )

        yield {
            "write_test_file": mock_write,
            "delete_document": mock_delete_doc,
            "delete_test_file": mock_delete_file,
            "client": mock_client
        }


def test_hello_r2r_main_success(mock_r2r_utils):
    """Test the hello_r2r main function with successful document creation."""
    with patch("builtins.print") as mock_print:
        hello_r2r_main()

        mock_r2r_utils["write_test_file"].assert_called_once()
        mock_r2r_utils["client"].retrieval.rag.assert_called_once()
        mock_r2r_utils["delete_document"].assert_called_once_with("doc123")
        mock_r2r_utils["delete_test_file"].assert_called_once()

        mock_print.assert_called_with("Completion:\nTest RAG answer")


def test_hello_r2r_main_no_document(mock_r2r_utils):
    """Test the hello_r2r main function when no document ID is returned."""
    with patch("src.engine.smoke_tests.hello_r2r.create_or_get_document", return_value=None), \
         patch("builtins.print") as mock_print:

        hello_r2r_main()

        mock_r2r_utils["client"].retrieval.rag.assert_not_called()

        mock_print.assert_called_with("Skipping RAG query: no document ID available.")

        mock_r2r_utils["delete_test_file"].assert_called_once()



def test_write_test_file():
    """Test the write_test_file function."""
    pass


def test_create_or_get_document():
    """Test the create_or_get_document function."""
    pass


def test_delete_document():
    """Test the delete_document function."""
    pass


def test_delete_test_file():
    """Test the delete_test_file function."""
    pass
