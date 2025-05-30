"""Unit tests for the config module."""

import logging
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from intake.config import (
    BASE_DIR,
    DATA_ROOT,
    DOWNLOAD_CHUNK_SIZE,
    DOWNLOAD_DELAY,
    DOWNLOAD_TIMEOUT,
    HAL_API_REQUEST_DELAY,
    HAL_API_TIMEOUT,
    HAL_API_URL,
    HAL_BATCH_SIZE,
    HAL_MAX_BATCHES,
    HAL_QUERY,
    LOG_FORMAT,
    LOG_FORMAT_SIMPLE,
    LOG_LEVEL,
    MAX_FILE_SIZE,
    PDF_DIR,
    PUBLICATIONS_FILE,
    R2R_API_PAGINATION_LIMIT,
    R2R_DEFAULT_BASE_URL,
    setup_logging,
)


def test_base_directories():
    """Test that base directories are properly defined."""
    assert isinstance(BASE_DIR, Path)
    assert isinstance(DATA_ROOT, Path)
    assert isinstance(PDF_DIR, Path)
    assert isinstance(PUBLICATIONS_FILE, Path)

    assert DATA_ROOT.is_relative_to(BASE_DIR)
    assert PDF_DIR.is_relative_to(DATA_ROOT)


def test_hal_api_settings():
    """Test HAL API settings are properly defined."""
    assert isinstance(HAL_API_URL, str)
    assert isinstance(HAL_QUERY, str)
    assert isinstance(HAL_BATCH_SIZE, int)
    assert isinstance(HAL_MAX_BATCHES, int)
    assert HAL_BATCH_SIZE > 0
    assert HAL_MAX_BATCHES > 0


def test_download_settings():
    """Test download settings are properly defined."""
    assert isinstance(DOWNLOAD_DELAY, int | float)
    assert isinstance(DOWNLOAD_TIMEOUT, int | float)
    assert isinstance(DOWNLOAD_CHUNK_SIZE, int)
    assert isinstance(HAL_API_TIMEOUT, int | float)
    assert isinstance(HAL_API_REQUEST_DELAY, int | float)
    assert DOWNLOAD_DELAY >= 0
    assert DOWNLOAD_TIMEOUT > 0
    assert DOWNLOAD_CHUNK_SIZE > 0
    assert HAL_API_TIMEOUT > 0
    assert HAL_API_REQUEST_DELAY >= 0


def test_r2r_settings():
    """Test R2R settings are properly defined."""
    assert isinstance(R2R_DEFAULT_BASE_URL, str)
    assert isinstance(MAX_FILE_SIZE, int)
    assert isinstance(R2R_API_PAGINATION_LIMIT, int)
    assert MAX_FILE_SIZE > 0
    assert R2R_API_PAGINATION_LIMIT > 0


def test_logging_settings():
    """Test logging settings are properly defined."""
    assert isinstance(LOG_LEVEL, int)
    assert isinstance(LOG_FORMAT, str)
    assert isinstance(LOG_FORMAT_SIMPLE, str)


def test_setup_logging_default():
    """Test setup_logging with default parameters."""
    with patch("src.intake.config.logging.basicConfig") as mock_config:
        setup_logging()

        mock_config.assert_called_once_with(level=LOG_LEVEL, format=LOG_FORMAT)


def test_setup_logging_custom_level():
    """Test setup_logging with custom log level."""
    custom_level = logging.DEBUG

    with patch("src.intake.config.logging.basicConfig") as mock_config:
        setup_logging(level=custom_level)

        mock_config.assert_called_once_with(level=custom_level, format=LOG_FORMAT)


def test_setup_logging_simple_format():
    """Test setup_logging with simple format."""
    with patch("src.intake.config.logging.basicConfig") as mock_config:
        setup_logging(simple_format=True)

        mock_config.assert_called_once_with(level=LOG_LEVEL, format=LOG_FORMAT_SIMPLE)


def test_setup_logging_requests_debug():
    """Test setup_logging with requests debug enabled."""
    with patch("src.intake.config.logging.basicConfig"), \
         patch("src.intake.config.logging.getLogger") as mock_get_logger:

        mock_requests_logger = MagicMock()
        mock_urllib3_logger = MagicMock()
        mock_get_logger.side_effect = [mock_requests_logger, mock_urllib3_logger]

        setup_logging(enable_requests_debug=True)

        mock_requests_logger.setLevel.assert_called_once_with(logging.DEBUG)
        mock_urllib3_logger.setLevel.assert_called_once_with(logging.DEBUG)
