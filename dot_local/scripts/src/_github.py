"""github.com access shared by the scripts in this directory."""

import os
import subprocess
from typing import Final

from github.Auth import Token
from truststore import inject_into_ssl


def get_auth() -> Token | None:
    if not (token := os.environ.get("GITHUB_TOKEN") or gh_auth_token()):
        return None
    inject_into_ssl()
    return Token(token)


def gh_auth_token() -> str | None:
    try:
        result: Final = subprocess.run(("gh", "auth", "token"), capture_output=True, check=True, text=True)
    except OSError, subprocess.CalledProcessError:
        return None
    return result.stdout.strip() or None


__all__ = ["get_auth"]
