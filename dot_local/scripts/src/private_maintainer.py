# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pygithub>=2.8.1",
#     "rich>=14.2",
#     "rich-argparse>=1.7.2",
#     "truststore>=0.10.4",
# ]
# ///

from __future__ import annotations

import os
import webbrowser
from argparse import ArgumentParser, Namespace
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

from github import Github
from github.Auth import Token
from github.GithubException import GithubException
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich_argparse import RichHelpFormatter
from truststore import inject_into_ssl

if TYPE_CHECKING:
    from github.PullRequest import PullRequest

# Mirrors the primary and maintenance projects in bernat-tech/data/projects.yaml (presentations excluded);
# keep both in sync. Monorepo components are covered by their parent repo (tox-dev/toml-fmt).
REPOSITORIES = [
    "tox-dev/platformdirs",
    "tox-dev/filelock",
    "pypa/virtualenv",
    "pypa/get-virtualenv",
    "tox-dev/tox",
    "tox-dev/pyproject-api",
    "pytest-dev/pytest-env",
    "koxudaxi/datamodel-code-generator",
    "tox-dev/pipdeptree",
    "tox-dev/sphinx-autodoc-typehints",
    "tox-dev/pre-commit-uv",
    "tox-dev/action-pre-commit-uv",
    "tox-dev/tox-uv",
    "tox-dev/toml-fmt",
    "tox-dev/pyproject-fmt",
    "tox-dev/tox-toml-fmt",
    "pytest-dev/pytest-print",
    "tox-dev/tox-gh",
    "tox-dev/sphinx-argparse-cli",
    "tox-dev/python-discovery",
    "tox-dev/devpi-process",
    "tox-dev/tox-ini-fmt",
    "gaborbernat/bump-deps-index",
    "gaborbernat/pypi-changes",
    "gaborbernat/mdformat-hugo",
    "tox-dev/mdformat-zola",
    "tox-dev/xml-fmt",
    "tox-dev/turbohtml",
    "tox-dev/PyVenvManage",
    "tox-dev/jetbrains-fish",
    "pypa/build",
    "pypa/pipx",
    "bloomberg/pytest-memray",
    "tox-dev/velodex",
    "gaborbernat/all-repos-self",
    "gaborbernat/bernat-tech",
    "gaborbernat/cv",
    "gaborbernat/ropi_jegyzet_latex",
    "gaborbernat/dotfiles",
    "gaborbernat/gaborbernat",
]

BOT_AUTHORS = frozenset({"dependabot[bot]", "pre-commit-ci[bot]"})


def main() -> None:
    opts = parse_cli()
    console = Console()

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        console.print("[red]GITHUB_TOKEN not set, cannot continue.[/red]")
        raise SystemExit(1)

    inject_into_ssl()

    try:
        run(console, token, opts)
    except KeyboardInterrupt:
        console.print("[red]Interrupted by user (Ctrl+C)[/red]")
    except GithubException as exc:
        console.print(f"[red]GitHub API error: {exc}[/red]")
        raise SystemExit(1) from exc


class Options(Namespace):
    dry_run: bool
    verbose: bool


def parse_cli() -> Options:
    parser = ArgumentParser(
        description="Review and auto-merge PRs across maintained repositories.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually merging")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    opts = Options()
    parser.parse_args(namespace=opts)
    return opts


def run(console: Console, token: str, opts: Options) -> None:
    """Main execution function."""
    console.print("[bold cyan]🔍 Scanning repositories for open PRs...[/bold cyan]")

    mergeable_prs, failed_prs = scan_repositories(console, token)

    console.print()
    console.print(f"[bold]Found {len(mergeable_prs)} mergeable PRs and {len(failed_prs)} failed PRs[/bold]")
    console.print()

    if mergeable_prs:
        display_mergeable_prs(console, mergeable_prs)
        process_mergeable_prs(console, opts, mergeable_prs)

    if failed_prs:
        display_failed_prs(console, failed_prs)
        if not opts.dry_run:
            open_failed_prs(console, failed_prs)

    if not mergeable_prs and not failed_prs:
        console.print("[green]✨ No open PRs found![/green]")


def scan_repositories(
    console: Console, token: str
) -> tuple[list[tuple[str, PullRequest, str]], list[tuple[str, PullRequest, str]]]:
    """Scan all repositories for open PRs and categorize them."""
    mergeable_prs: list[tuple[str, PullRequest, str]] = []
    failed_prs: list[tuple[str, PullRequest, str]] = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Scanning repositories...", total=len(REPOSITORIES))

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_repo = {
                executor.submit(scan_single_repository, token, repo_path): repo_path for repo_path in REPOSITORIES
            }

            for future in as_completed(future_to_repo):
                repo_path = future_to_repo[future]
                try:
                    repo_mergeable, repo_failed, pr_titles, repo_name = future.result()
                    mergeable_prs.extend(repo_mergeable)
                    failed_prs.extend(repo_failed)

                    if pr_titles:
                        pr_word = "PR" if len(pr_titles) == 1 else "PRs"
                        console.print(f"[green]✓[/green] {repo_name}: {len(pr_titles)} open {pr_word}")
                        for title in pr_titles:
                            console.print(f"  [dim]{title}[/dim]")

                except (GithubException, OSError, ValueError) as e:
                    console.print(f"[yellow]⚠ {repo_path}: Could not fetch PRs ({e})[/yellow]")

                progress.advance(task)

    return mergeable_prs, failed_prs


def scan_single_repository(
    token: str, repo_path: str
) -> tuple[list[tuple[str, PullRequest, str]], list[tuple[str, PullRequest, str]], list[str], str]:
    """Scan a single repository for PRs. Uses a per-thread client (PyGithub sessions aren't shared-safe)."""
    repo = Github(auth=Token(token)).get_repo(repo_path)
    repo_name = repo.name
    prs = repo.get_pulls(state="open", sort="created", direction="asc")

    mergeable_prs: list[tuple[str, PullRequest, str]] = []
    failed_prs: list[tuple[str, PullRequest, str]] = []
    pr_titles: list[str] = []

    for pr in prs:
        if pr.draft:
            continue
        if (user := pr.user) is None or user.type != "Bot" or user.login not in BOT_AUTHORS:
            continue

        check_status, reason, checked_sha = check_pr_status(pr)
        if check_status == "success":
            assert checked_sha is not None
            mergeable_prs.append((repo_name, pr, checked_sha))
        else:
            failed_prs.append((repo_name, pr, reason))

        pr_titles.append(f"#{pr.number} {pr.title}")

    return mergeable_prs, failed_prs, pr_titles, repo_name


def display_mergeable_prs(console: Console, mergeable_prs: list[tuple[str, PullRequest, str]]) -> None:
    """Display table of PRs that can be auto-merged."""
    console.print("[bold green]✅ Mergeable PRs (all checks passing):[/bold green]")
    table = Table(show_header=True)
    table.add_column("Repository", style="cyan")
    table.add_column("PR #", style="magenta")
    table.add_column("Title", style="yellow")
    table.add_column("Author", style="blue")

    for repo_name, pr, _checked_sha in mergeable_prs:
        table.add_row(repo_name, f"#{pr.number}", pr.title, pr.user.login if pr.user else "unknown")

    console.print(table)
    console.print()


def process_mergeable_prs(console: Console, opts: Options, mergeable_prs: list[tuple[str, PullRequest, str]]) -> None:
    """Approve and merge PRs or show what would be done in dry-run mode."""
    for repo_name, pr, checked_sha in mergeable_prs:
        if opts.dry_run:
            console.print(f"[dim][DRY RUN] Would approve and merge {repo_name}#{pr.number}[/dim]")
        else:
            approve_and_merge(console, repo_name, pr, checked_sha)


def display_failed_prs(console: Console, failed_prs: list[tuple[str, PullRequest, str]]) -> None:
    """Display table of PRs that need manual review."""
    console.print("[bold yellow]⚠️  PRs requiring manual review:[/bold yellow]")
    table = Table(show_header=True)
    table.add_column("Repository", style="cyan")
    table.add_column("PR #", style="magenta")
    table.add_column("Title", style="yellow")
    table.add_column("Reason", style="red")

    for repo_name, pr, reason in failed_prs:
        table.add_row(repo_name, f"#{pr.number}", pr.title, reason)

    console.print(table)
    console.print()


def open_failed_prs(console: Console, failed_prs: list[tuple[str, PullRequest, str]]) -> None:
    """Open PRs that need manual review in browser."""
    console.print("[bold]Opening failed PRs in browser...[/bold]")
    for repo_name, pr, _reason in failed_prs:
        console.print(f"[dim]Opening {repo_name}#{pr.number}...[/dim]")
        webbrowser.open(pr.html_url)


def check_pr_status(pr: PullRequest) -> tuple[str, str, str | None]:  # noqa: PLR0911
    """
    Check if a PR is ready to merge.

    Returns a tuple of (status, reason) where status is one of:
    - "success": All checks passed, ready to merge
    - "failed": Some checks failed or other issues

    The reason provides details when status is "failed".
    """
    # mergeable is True/False/None; None means GitHub hasn't computed it yet, so don't act on stale data.
    if pr.mergeable is not True or pr.mergeable_state in ("unknown", "dirty"):
        return "failed", f"Not mergeable (mergeable={pr.mergeable}, state={pr.mergeable_state})", None

    # Evaluate CI on the true head commit, not get_commits()[-1] (truncated past 250 commits).
    head_commit = pr.base.repo.get_commit(pr.head.sha)
    combined_status = head_commit.get_combined_status()
    check_runs = head_commit.get_check_runs()

    legacy_statuses = combined_status.statuses
    check_run_list = list(check_runs)

    if not legacy_statuses and not check_run_list:
        return "failed", "No CI checks found", None

    for status in legacy_statuses:
        if status.state in ("error", "failure"):
            return "failed", f"Check failed: {status.context}", None
        if status.state == "pending":
            return "failed", f"Check pending: {status.context}", None

    for check_run in check_run_list:
        if check_run.status != "completed":
            return "failed", f"Check not completed: {check_run.name}", None
        if check_run.conclusion not in ("success", "neutral", "skipped"):
            return "failed", f"Check failed: {check_run.name} ({check_run.conclusion})", None

    return "success", "", pr.head.sha


def approve_and_merge(console: Console, repo_name: str, pr: PullRequest, checked_sha: str) -> None:
    """Approve a PR with LGTM comment and merge it."""
    try:
        pr_link = f"[link={pr.html_url}]{repo_name}#{pr.number}[/link]"

        console.print(f"[green]✓ Approving {pr_link}...[/green]")
        pr.create_review(body="LGTM", event="APPROVE")

        console.print(f"[green]✓ Merging {pr_link}...[/green]")
        merge_result = pr.merge(sha=checked_sha, merge_method="squash")

        if merge_result.merged:
            console.print(f"[bold green]✅ Successfully merged {pr_link}![/bold green]")
        else:
            console.print(f"[yellow]⚠ Could not merge {pr_link}: {merge_result.message}[/yellow]")

    except GithubException as e:
        pr_link = f"[link={pr.html_url}]{repo_name}#{pr.number}[/link]"
        console.print(f"[red]❌ Failed to approve/merge {pr_link}: {e}[/red]")


if __name__ == "__main__":
    main()
