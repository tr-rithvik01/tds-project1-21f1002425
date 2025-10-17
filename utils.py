import base64
from typing import Optional, Tuple

def decode_attachment(attachment: dict) -> Optional[Tuple[str, bytes]]:
    """Decodes a data URI from an attachment dictionary."""
    file_name = attachment.get('name')
    data_uri = attachment.get('url')

    if not file_name or not data_uri or "," not in data_uri:
        return None

    header, encoded = data_uri.split(",", 1)
    decoded_content = base64.b64decode(encoded)

    return file_name, decoded_content