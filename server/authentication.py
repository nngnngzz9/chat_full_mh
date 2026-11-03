
import secrets
import hashlib
import hmac


def generate_receiver_id():
    return str(secrets.randbelow(900_000_000) + 100_000_000)


def generate_salt():
    return secrets.token_bytes(16)


def hash_password(password, salt=None):
    if not isinstance(password, str) or len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")

    if salt is None:
        salt = generate_salt()

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        600_000
    )

    return salt.hex(), password_hash.hex()


def verify_password(password, salt_hex, stored_hash):
    try:
        salt = bytes.fromhex(salt_hex)

        _, password_hash = hash_password(
            password,
            salt
        )

        return hmac.compare_digest(
            password_hash,
            stored_hash
        )

    except (ValueError, TypeError):
        return False
