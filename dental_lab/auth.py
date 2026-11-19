"""Password storage for the local laboratory account, separate from the API key."""
import hashlib
import hmac
import secrets

ITERATIONS = 600_000


def hash_password(password: str) -> str:
    if not isinstance(password, str) or not 1 <= len(password) <= 1024:
        raise ValueError('La contraseña debe tener entre 1 y 1024 caracteres')
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
    return f'pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split('$')
        if algorithm != 'pbkdf2_sha256' or not 100_000 <= int(rounds) <= 2_000_000:
            return False
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
        if len(salt) != 16 or len(expected) != 32 or not 1 <= len(password) <= 1024:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (AttributeError, TypeError, ValueError):
        return False


def same_username(provided: str, expected: str) -> bool:
    return hmac.compare_digest(provided.strip().casefold().encode('utf-8'),
                               expected.strip().casefold().encode('utf-8'))
