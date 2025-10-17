import os
import base64
from pathlib import Path

TMP_DIR = Path("/tmp/llm_deployer_attachments")
TMP_DIR.mkdir(parents=True, exist_ok=True)

def save_attachments_to_disk(attachments: list) -> list:
    """
    Decodes base64 attachments and saves them to a temporary directory on disk.

    Args:
        attachments: A list of attachment dictionaries from the request.

    Returns:
        A list of metadata dictionaries for the saved files, including their temp path.
    """
    saved_files_meta = []
    if not attachments:
        return saved_files_meta

    for att in attachments:
        name = att.get("name")
        url = att.get("url")
        if not name or not url or not url.startswith("data:"):
            continue
        try:
            header, b64data = url.split(",", 1)
            data = base64.b64decode(b64data)
            path = TMP_DIR / name
            with open(path, "wb") as f:
                f.write(data)
            saved_files_meta.append({
                "name": name,
                "path": str(path),
                "size": len(data)
            })
        except Exception as e:
            print(f"Warning: Failed to decode and save attachment '{name}': {e}")
    return saved_files_meta

def cleanup_attachments(saved_files_meta: list):
    """
    Deletes the temporary files created for attachments.
    """
    if not saved_files_meta:
        return

    print("Cleaning up temporary attachment files...")
    for meta in saved_files_meta:
        try:
            os.remove(meta["path"])
        except OSError as e:
            print(f"Warning: Could not remove temp file '{meta['path']}': {e}")