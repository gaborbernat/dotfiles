import subprocess
from typing import TYPE_CHECKING

import pytest

from _github import get_auth

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def inject_into_ssl(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("_github.inject_into_ssl", autospec=True)


def test_get_auth_prefers_environment(monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "environment-token")
    gh = mocker.patch("_github.subprocess.run", autospec=True)

    assert (auth := get_auth()) is not None
    assert auth.token == "environment-token"
    gh.assert_not_called()


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        pytest.param("gh-token\n", "gh-token", id="gh token"),
        pytest.param("\n", None, id="empty gh output"),
    ],
)
def test_get_auth_uses_gh_auth(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, stdout: str, expected: str | None
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "")
    completed = subprocess.CompletedProcess(("gh", "auth", "token"), 0, stdout=stdout)
    mocker.patch("_github.subprocess.run", autospec=True, return_value=completed)

    assert (auth.token if (auth := get_auth()) else None) == expected


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(FileNotFoundError(), id="gh missing"),
        pytest.param(subprocess.CalledProcessError(1, ("gh", "auth", "token")), id="gh not authenticated"),
    ],
)
def test_get_auth_handles_gh_failure(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, error: OSError | subprocess.CalledProcessError
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "")
    mocker.patch("_github.subprocess.run", autospec=True, side_effect=error)

    assert get_auth() is None


@pytest.mark.parametrize(
    ("token", "injected"),
    [
        pytest.param("environment-token", 1, id="token found"),
        pytest.param("", 0, id="no token"),
    ],
)
def test_get_auth_trusts_system_certificates_only_with_token(
    monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture, inject_into_ssl: MagicMock, token: str, injected: int
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", token)
    mocker.patch("_github.subprocess.run", autospec=True, side_effect=FileNotFoundError())

    get_auth()

    assert inject_into_ssl.call_count == injected
