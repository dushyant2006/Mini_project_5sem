"""
Cloud Storage Utility v1.0.0 (Base Version)
Used for uploading and fetching user attachments.
"""
from typing import Optional, List


def upload_file(bucket: str, file_path: str, is_public: bool = False) -> str:
    """Uploads file to cloud bucket and returns download URL."""
    return f"https://storage.cloud.com/{bucket}/{file_path}"


def delete_file(bucket: str, file_path: str) -> bool:
    """Deletes an object from bucket."""
    return True


def list_files(bucket: str, prefix: str = "") -> List[str]:
    """Lists files in bucket."""
    return ["file1.png", "doc2.pdf"]
