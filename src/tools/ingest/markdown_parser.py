"""Markdown file parsing with YAML frontmatter extraction."""
import frontmatter
import yaml
from pathlib import Path
from typing import Tuple
from models.speech import SpeechFrontmatter

def parse_markdown_file(file_path: str) -> Tuple[SpeechFrontmatter, str]:
    """Parse markdown file with YAML frontmatter."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")

    try:
        with open(path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid frontmatter: Malformed YAML - {e}")
    
    if not post.metadata:
        raise ValueError("Markdown file missing YAML frontmatter")
    
    try:
        metadata = SpeechFrontmatter(**post.metadata)
    except Exception as e:
        raise ValueError(f"Invalid frontmatter: {e}")
    
    content = post.content.strip()
    if not content:
        raise ValueError("Speech text content is empty")
    
    return metadata, content
