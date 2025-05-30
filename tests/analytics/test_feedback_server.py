"""Unit tests for the feedback_server module."""

import os
import sys
from unittest.mock import MagicMock, mock_open, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from analytics.feedback_server import app, view_feedback


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_receive_feedback_new_file(test_client):
    """Test receiving feedback when the CSV file doesn't exist yet."""
    feedback_data = {
        "question": "Test question?",
        "answer": "Test answer.",
        "feedback": "up",
        "timestamp": "2023-01-01T12:00:00Z"
    }

    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()) as mock_file, \
         patch("csv.writer") as mock_writer:

        mock_csv_writer = MagicMock()
        mock_writer.return_value = mock_csv_writer

        response = test_client.post("/v1/feedback", json=feedback_data)

        assert response.status_code == 200
        assert response.json() == {"message": "Feedback saved"}

        mock_file.assert_called_once_with("feedback.csv", "a", newline='', encoding='utf-8')

        mock_csv_writer.writerow.assert_any_call(["timestamp", "feedback", "question", "answer"])

        mock_csv_writer.writerow.assert_any_call([
            "2023-01-01T12:00:00Z", "up", "Test question?", "Test answer."
        ])


def test_receive_feedback_existing_file(test_client):
    """Test receiving feedback when the CSV file already exists."""
    feedback_data = {
        "question": "Test question?",
        "answer": "Test answer.",
        "feedback": "down",
        "timestamp": "2023-01-01T12:00:00Z"
    }

    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open()) as mock_file, \
         patch("csv.writer") as mock_writer:

        mock_csv_writer = MagicMock()
        mock_writer.return_value = mock_csv_writer

        response = test_client.post("/v1/feedback", json=feedback_data)

        assert response.status_code == 200
        assert response.json() == {"message": "Feedback saved"}

        mock_file.assert_called_once_with("feedback.csv", "a", newline='', encoding='utf-8')

        mock_csv_writer.writerow.assert_called_once_with([
            "2023-01-01T12:00:00Z", "down", "Test question?", "Test answer."
        ])


def test_receive_feedback_invalid_data(test_client):
    """Test receiving invalid feedback data."""
    feedback_data = {
        "question": "Test question?",
        "answer": "Test answer.",
        "timestamp": "2023-01-01T12:00:00Z"
    }

    response = test_client.post("/v1/feedback", json=feedback_data)

    assert response.status_code == 422  # Validation error


def test_receive_feedback_invalid_feedback_value(test_client):
    """Test receiving feedback with invalid feedback value."""
    feedback_data = {
        "question": "Test question?",
        "answer": "Test answer.",
        "feedback": "invalid",  # Not "up" or "down"
        "timestamp": "2023-01-01T12:00:00Z"
    }

    response = test_client.post("/v1/feedback", json=feedback_data)

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_view_feedback_no_file():
    """Test viewing feedback when no CSV file exists."""
    with patch("os.path.exists", return_value=False):
        response = await view_feedback()

        assert response == "<h3>No feedback recorded yet.</h3>"


@pytest.mark.asyncio
async def test_view_feedback_with_data():
    """Test viewing feedback with existing data."""
    csv_data = [
        ["timestamp", "feedback", "question", "answer"],
        ["2023-01-01T12:00:00Z", "up", "Question 1?", "Answer 1."],
        ["2023-01-02T12:00:00Z", "down", "Question 2?", "Answer 2."]
    ]

    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open()), \
         patch("csv.reader") as mock_reader:

        mock_reader.return_value = csv_data

        response = await view_feedback()

        assert "<h2>Feedback Table</h2>" in response
        assert "<table border='1' cellpadding='5'>" in response
        assert "<th>timestamp</th>" in response
        assert "<td>Question 1?</td>" in response
        assert "<td>Answer 2.</td>" in response


def test_view_feedback_endpoint(test_client):
    """Test the view_feedback endpoint."""
    with patch("src.analytics.feedback_server.view_feedback", return_value="<h2>Test HTML</h2>"):
        response = test_client.get("/v1/feedback/view")

        assert response.status_code == 200
        assert response.text == "<h2>Test HTML</h2>"
        assert response.headers["content-type"] == "text/html; charset=utf-8"
