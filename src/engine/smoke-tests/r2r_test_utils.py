# r2r_test_utils.py
"""Utility functions for R2R smoke testing."""

import os
import re
import time
from pathlib import Path

from r2r import R2RClient

# Load configuration from common file
config_path = Path(__file__).parent.parent / "common_config.sh"
config = {}
if config_path.exists():
    with open(config_path) as f:
        for line in f:
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.strip().split("=", 1)
                config[key] = value.strip('"')

SERVER_URL = config.get("SERVER_URL", "http://localhost:7272")
TEST_FILE = config.get("TEST_FILE", "test.txt")
TEST_CONTENT = config.get("TEST_CONTENT", "QuetzalX is a person that works at CIRED.")
QUERY = config.get("TEST_QUERY", "Who is QuetzalX?")
MODEL = "openai/gpt-4o-mini"
TEMPERATURE = 0.0
DOCUMENT_POLLING_TIMEOUT = 30  # seconds
DOCUMENT_POLLING_INTERVAL = 2  # seconds

client = R2RClient(SERVER_URL)


def write_test_file(content: str = TEST_CONTENT) -> None:
    """
    Create a test file with the specified content.

    Args:
    ----
        content: The string content to write into the test file.

    """
    with open(TEST_FILE, "w") as file:
        file.write(content)
        print(f"Local file created: {content}")


def delete_test_file() -> None:
    """Delete the local test file, if it exists."""
    try:
        os.remove(TEST_FILE)
        print("Local file deleted.")
    except Exception as e:
        print(f"Warning: Failed to delete local file: {e}")


# Deprecated: Not currently used
def find_document_by_title(title: str = TEST_FILE) -> str | None:
    """
    Search for a document by title and return its ID if found.

    Args:
    ----
        title: Title of the document to find.

    Returns:
    -------
        The document ID if found, else None.

    """
    limit, offset = 100, 0
    while True:
        response, _ = client.documents.list(limit=limit, offset=offset)
        for doc in response[1]:
            if doc.title == title:
                return doc.id
        if len(response[1]) < limit:
            break
        offset += limit
    return None


def create_or_get_document() -> str | None:
    """
    Create a document from the test file or retrieve its existing ID.

    Returns
    -------
        The document ID if creation or extraction succeeds, else None.

    """
    try:
        response = client.documents.create(file_path=TEST_FILE)
        document_id = response.results.document_id
        print("Document created.")

        start_time = time.time()
        while time.time() - start_time < DOCUMENT_POLLING_TIMEOUT:
            try:
                doc_info = client.documents.retrieve(document_id)
                ingestion_status = getattr(doc_info.results, 'ingestion_status', 'unknown')

                print(f"Document status: ingestion={ingestion_status}")

                if ingestion_status == "success":
                    print("Document is ready.")
                    return document_id
                elif ingestion_status == "failed":
                    print(f"Document processing failed: ingestion={ingestion_status}")
                    return None

                time.sleep(DOCUMENT_POLLING_INTERVAL)
            except Exception as poll_error:
                print(f"Error checking document status: {poll_error}")
                time.sleep(DOCUMENT_POLLING_INTERVAL)

        print(f"Timeout waiting for document to be ready after {DOCUMENT_POLLING_TIMEOUT} seconds")
        return document_id
    except Exception as e:
        error_msg = str(e)
        if "already exists" in error_msg:
            print("Document already exists. Extracting ID...")
            match = re.search(r"Document ([\w-]+) already exists", error_msg)
            if match:
                document_id = match.group(1)
                print(f"Found existing document ID: {document_id}")
                return document_id
            print("Error: Could not parse document ID from error message.")
        else:
            print(f"Unexpected creation error: {e}")
    return None


def delete_document(doc_id: str) -> None:
    """
    Delete a document from the R2R server by ID.

    Args:
    ----
        doc_id: The ID of the document to delete.

    """
    try:
        client.documents.delete(doc_id)
        print("Document deleted from server.")
    except Exception as e:
        print(f"Warning: Failed to delete document: {e}")
