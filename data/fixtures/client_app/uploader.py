"""
Client Document Uploader Module consuming storage_lib.
"""
from storage_lib import upload_file, list_files


def handle_attachment_upload(filename: str) -> str:
    """Safe: Calls upload_file with bucket and file_path."""
    return upload_file(bucket="user_docs", file_path=filename)
