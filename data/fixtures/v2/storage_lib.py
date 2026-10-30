"""
Cloud Storage Utility v1.1.0 (Compatible Minor Version Bump)
"""
from typing import Optional, List


def upload_file(bucket: str, file_path: str, is_public: bool = False, encryption: str = "AES256") -> str:
    """
    COMPATIBLE: 'encryption' added with default value.
    """
    return f"https://storage.cloud.com/{bucket}/{file_path}?enc={encryption}"


def delete_file(bucket: str, file_path: str) -> bool:
    """COMPATIBLE: Unchanged."""
    return True


def list_files(bucket: str, prefix: str = "", max_items: int = 100) -> List[str]:
    """
    COMPATIBLE: 'max_items' added with default value.
    """
    return ["file1.png", "doc2.pdf"]
