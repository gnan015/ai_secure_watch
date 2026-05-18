def mask_secret(secret: str) -> str:
    """Mask a secret so logs never expose the full value."""
    if not secret:
        return ""

    secret_length = len(secret)

    if secret_length == 1:
        return "*"

    if secret_length == 2:
        return f"{secret[0]}*"

    if secret_length <= 6:
        middle_mask = "*" * (secret_length - 2)
        return f"{secret[0]}{middle_mask}{secret[-1]}"

    middle_mask = "*" * (secret_length - 8)
    return f"{secret[:4]}{middle_mask}{secret[-4:]}"
