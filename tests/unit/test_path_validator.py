"""Unit tests for path validator."""
import pytest
from pathlib import Path
from tools.ingestion_utils.path_validator import validate_file_path
from unittest.mock import patch


def test_validate_path_within_base():
    """Test validating path within base directory."""
    with patch('tools.ingestion_utils.path_validator.get_ingestion_base_dir', return_value='/data/hansard'):
        result = validate_file_path('/data/hansard/speeches/test.md')
        assert isinstance(result, Path)


def test_validate_path_outside_base():
    """Test validating path outside base directory raises error."""
    with patch('tools.ingestion_utils.path_validator.get_ingestion_base_dir', return_value='/data/hansard'):
        with pytest.raises(ValueError, match="outside allowed directory"):
            validate_file_path('/etc/passwd')


def test_validate_path_traversal_attack():
    """Test path traversal prevention."""
    with patch('tools.ingestion_utils.path_validator.get_ingestion_base_dir', return_value='/data/hansard'):
        with pytest.raises(ValueError, match="outside allowed directory"):
            validate_file_path('/data/hansard/../../../etc/passwd')


def test_validate_path_disabled():
    """Test validation can be disabled."""
    result = validate_file_path('/any/path/test.md', validate_path=False)
    assert isinstance(result, Path)
