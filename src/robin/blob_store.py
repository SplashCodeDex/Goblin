import os
import gzip
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Get the directory of the current script
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_current_dir))
BLOB_DIR = os.path.join(_project_root, "data", "blobs")

class BlobStore:
    """
    Handles storage and retrieval of large content blobs using GZIP compression.
    """
    
    @staticmethod
    def _ensure_dir():
        if not os.path.exists(BLOB_DIR):
            os.makedirs(BLOB_DIR, exist_ok=True)

    @classmethod
    def save_blob(cls, external_id: str, source_name: str, content: str) -> Optional[str]:
        """
        Saves content to a compressed file and returns the relative path.
        """
        cls._ensure_dir()
        
        # Clean filename
        safe_id = "".join(c for c in f"{source_name}_{external_id}" if c.isalnum() or c in ('_', '-'))
        filename = f"{safe_id}.gz"
        filepath = os.path.join(BLOB_DIR, filename)
        
        try:
            with gzip.open(filepath, 'wt', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"Saved blob to {filepath}")
            return f"data/blobs/{filename}"
        except Exception as e:
            logger.error(f"Failed to save blob: {e}")
            return None

    @classmethod
    def read_blob(cls, relative_path: str) -> Optional[str]:
        """
        Reads content from a compressed blob file.
        """
        # Ensure path is relative to project root
        filepath = os.path.join(_project_root, relative_path)
        
        if not os.path.exists(filepath):
            logger.error(f"Blob file not found: {filepath}")
            return None
            
        try:
            with gzip.open(filepath, 'rt', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read blob: {e}")
            return None

def get_leak_content(leak_row: dict) -> Optional[str]:
    """
    Unified helper to get content whether it's in DB or in a Blob.
    """
    content = leak_row.get('content', '')
    if content and content.startswith("data/blobs/"):
        return BlobStore.read_blob(content)
        
    return content if content else None
