"""Path validation with directory traversal prevention."""
from pathlib import Path
from config import get_ingestion_base_dir

def validate_file_path(file_path: str, validate_path: bool = True) -> Path:
    """Validate file path for security.
    
    Args:
        file_path: Path to validate
        validate_path: Whether to enforce base directory check
        
    Returns:
        Resolved absolute Path object
        
    Raises:
        ValueError: If path is outside allowed directory
    """
    path = Path(file_path).resolve()
    
    if not validate_path:
        return path
    
    base_dir = Path(get_ingestion_base_dir()).resolve()
    
    # Check if path is within base directory
    try:
        path.relative_to(base_dir)
    except ValueError:
        raise ValueError(f"Path outside allowed directory: {file_path}")
    
    return path
