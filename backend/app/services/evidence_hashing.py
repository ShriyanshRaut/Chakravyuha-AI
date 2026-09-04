import hashlib

def calculate_sha256(file_bytes: bytes) -> str:
    """Computes SHA-256 fingerprint for a raw evidence file stream."""
    sha256_hash = hashlib.sha256()
    sha256_hash.update(file_bytes)
    return sha256_hash.hexdigest()