# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "pygithub>=2.10.0",
#     "rich>=15.0.0",
#     "rich-argparse>=1.8.0",
#     "truststore>=0.10.4",
# ]
# ///

import os
import subprocess
import webbrowser
from argparse import ArgumentParser, Namespace
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING, Final

from github import Github
from github.Auth import Token
from github.GithubException import GithubException
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text
from rich_argparse import RichHelpFormatter
from truststore import inject_into_ssl

if TYPE_CHECKING:
    from github.CheckRun import CheckRun
    from github.CommitStatus import CommitStatus
    from github.PullRequest import PullRequest
    from github.WorkflowRun import WorkflowRun


def main() -> None:
    opts: Final = parse_cli()
    console: Final = Console()
    if not (token := get_token()):
        console.print("[red]No GitHub token found. Set GITHUB_TOKEN or run gh auth login.[/red]")
        raise SystemExit(1)
    inject_into_ssl()
    try:
        run(console, token, opts)
    except KeyboardInterrupt:
        console.print("[red]Interrupted by user (Ctrl+C)[/red]")
    except GithubException as exc:
        console.print(f"[red]GitHub API error: {exc}[/red]")
        raise SystemExit(1) from exc


def parse_cli() -> Options:
    parser: Final = ArgumentParser(
        description="Review and auto-merge PRs across maintained repositories.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without actually merging")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args(namespace=Options())


class Options(Namespace):
    dry_run: bool
    verbose: bool


def get_token() -> str | None:
    if token := os.environ.get("GITHUB_TOKEN"):
        return token
    try:
        result: Final = subprocess.run(("gh", "auth", "token"), capture_output=True, check=True, text=True)
    except OSError, subprocess.CalledProcessError:
        return None
    return result.stdout.strip() or None


def run(console: Console, token: str, opts: Options) -> None:
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
) -> tuple[list[tuple[str, PullRequest, str]], list[tuple[str, PullRequest, str, str | None]]]:
    # Mirrors the primary and maintenance projects in bernat-tech/data/projects.yaml (presentations excluded);
    # keep both in sync. toml-fmt covers its monorepo components; pyproject-fmt and tox-toml-fmt are listed
    # separately because the pre-commit hook mirrors are their own repos and get their own bot PRs.
    repositories: Final = (
        "tox-dev/platformdirs",
        "tox-dev/filelock",
        "pypa/virtualenv",
        "pypa/get-virtualenv",
        "tox-dev/tox",
        "tox-dev/pyproject-api",
        "pytest-dev/pytest-env",
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
        "tox-dev/xml-fmt",
        "tox-dev/turbohtml",
        "tox-dev/peryx",
        "tox-dev/mdformat-zola",
        "tox-dev/PyVenvManage",
        "tox-dev/jetbrains-fish",
        "pypa/build",
        "pypa/pipx",
        "bloomberg/pytest-memray",
        "gaborbernat/all-repos-self",
        "gaborbernat/bernat-tech",
        "gaborbernat/cv",
        "gaborbernat/ropi_jegyzet_latex",
        "gaborbernat/dotfiles",
        "gaborbernat/gaborbernat",
    )
    mergeable_prs: Final[list[tuple[str, PullRequest, str]]] = []
    failed_prs: Final[list[tuple[str, PullRequest, str, str | None]]] = []
    with (
        Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress,
        ThreadPoolExecutor(max_workers=10) as executor,
    ):
        task = progress.add_task("Scanning repositories...", total=len(repositories))
        future_to_repo = {
            executor.submit(scan_single_repository, token, repo_path): repo_path for repo_path in repositories
        }
        for future in as_completed(future_to_repo):
            try:
                repo_mergeable, repo_failed, pr_titles, repo_name = future.result()
            except (GithubException, OSError, ValueError) as exc:
                console.print(f"[yellow]⚠ {future_to_repo[future]}: Could not fetch PRs ({exc})[/yellow]")
            else:
                mergeable_prs.extend(repo_mergeable)
                failed_prs.extend(repo_failed)
                if pr_titles:
                    console.print(
                        f"[green]✓[/green] {repo_name}: {len(pr_titles)} open {'PR' if len(pr_titles) == 1 else 'PRs'}"
                    )
                    for title in pr_titles:
                        console.print(f"  [dim]{title}[/dim]")
            progress.advance(task)
    return mergeable_prs, failed_prs


def scan_single_repository(
    token: str, repo_path: str
) -> tuple[list[tuple[str, PullRequest, str]], list[tuple[str, PullRequest, str, str | None]], list[str], str]:
    # A client per thread, since PyGithub sessions are not safe to share across threads
    repo: Final = Github(auth=Token(token)).get_repo(repo_path)
    mergeable_prs: Final[list[tuple[str, PullRequest, str]]] = []
    failed_prs: Final[list[tuple[str, PullRequest, str, str | None]]] = []
    pr_titles: Final[list[str]] = []
    for pr in repo.get_pulls(state="open", sort="created", direction="asc"):
        if pr.draft or pr.user.type != "Bot" or pr.user.login not in {"dependabot[bot]", "pre-commit-ci[bot]"}:
            continue
        if (failure := check_pr_status(pr)) is None:
            mergeable_prs.append((repo.name, pr, pr.head.sha))
        else:
            failed_prs.append((repo.name, pr, *failure))
        pr_titles.append(f"#{pr.number} {pr.title}")
    return mergeable_prs, failed_prs, pr_titles, repo.name


def check_pr_status(pr: PullRequest) -> tuple[str, str | None] | None:
    # mergeable is None while GitHub is still computing it, so do not act on stale data
    if pr.mergeable is not True or pr.mergeable_state in {"unknown", "dirty"}:
        return f"Not mergeable (mergeable={pr.mergeable}, state={pr.mergeable_state})", None
    # get_commits()[-1] is truncated past 250 commits, so read CI from the head commit itself
    head_commit: Final = pr.base.repo.get_commit(pr.head.sha)
    if (current := current_check_runs(pr, list(head_commit.get_check_runs()))) is None:
        return "No GitHub Actions runs found", None
    check_runs, workflows = current
    combined_status: Final = head_commit.get_combined_status()
    latest_statuses: Final = {
        status.context: status for status in sorted(combined_status.statuses, key=lambda item: item.id)
    }
    latest_check_runs: Final = {
        (check_run.app.id, check_run.name): check_run for check_run in sorted(check_runs, key=lambda item: item.id)
    }
    return check_failure(list(latest_statuses.values()), list(latest_check_runs.values())) or workflow_failure(
        workflows
    )


def current_check_runs(pr: PullRequest, check_runs: list[CheckRun]) -> tuple[list[CheckRun], list[WorkflowRun]] | None:
    if not any(check_run.app.slug == "github-actions" for check_run in check_runs):
        return check_runs, []
    latest: Final[dict[tuple[int, str], WorkflowRun]] = {}
    for workflow in sorted(pr.base.repo.get_workflow_runs(head_sha=pr.head.sha), key=lambda item: item.id):
        latest[workflow.workflow_id, workflow.event] = workflow
    if not latest:
        return None
    suites: Final = {workflow.check_suite_id for workflow in latest.values()}
    return (
        [
            check_run
            for check_run in check_runs
            if check_run.app.slug != "github-actions" or check_run.check_suite.id in suites
        ],
        list(latest.values()),
    )


def check_failure(statuses: list[CommitStatus], check_runs: list[CheckRun]) -> tuple[str, str | None] | None:
    if not statuses and not check_runs:
        return "No CI checks found", None
    for status in statuses:
        if status.state in {"error", "failure"}:
            return f"Check failed: {status.context}", status.target_url
        if status.state == "pending":
            return f"Check pending: {status.context}", status.target_url
    for check_run in check_runs:
        if check_run.status != "completed":
            return f"Check not completed: {check_run.name}", check_run.details_url
        if check_run.conclusion not in {"success", "neutral", "skipped"}:
            return f"Check failed: {check_run.name} ({check_run.conclusion})", check_run.details_url
    return None


def workflow_failure(workflows: list[WorkflowRun]) -> tuple[str, str] | None:
    for workflow in workflows:
        if workflow.status != "completed":
            return f"Workflow not completed: {workflow.name}", workflow.html_url
        if workflow.conclusion not in {"success", "neutral", "skipped"}:
            return f"Workflow failed: {workflow.name} ({workflow.conclusion})", workflow.html_url
    return None


def display_mergeable_prs(console: Console, mergeable_prs: list[tuple[str, PullRequest, str]]) -> None:
    console.print("[bold green]✅ Mergeable PRs (all checks passing):[/bold green]")
    table: Final = Table(show_header=True)
    table.add_column("Repository", style="cyan")
    table.add_column("PR #", style="magenta")
    table.add_column("Title", style="yellow")
    table.add_column("Author", style="blue")
    for repo_name, pr, _ in mergeable_prs:
        table.add_row(repo_name, Text(f"#{pr.number}", style=f"link {pr.html_url}"), pr.title, pr.user.login)
    console.print(table)
    console.print()


def process_mergeable_prs(console: Console, opts: Options, mergeable_prs: list[tuple[str, PullRequest, str]]) -> None:
    for repo_name, pr, checked_sha in mergeable_prs:
        if opts.dry_run:
            console.print(f"[dim][DRY RUN] Would approve and merge {repo_name}#{pr.number}[/dim]")
        else:
            approve_and_merge(console, repo_name, pr, checked_sha)


def approve_and_merge(console: Console, repo_name: str, pr: PullRequest, checked_sha: str) -> None:
    pr_link: Final = f"[link={pr.html_url}]{repo_name}#{pr.number}[/link]"
    try:
        console.print(f"[green]✓ Approving {pr_link}...[/green]")
        pr.create_review(body="LGTM", event="APPROVE")
        console.print(f"[green]✓ Merging {pr_link}...[/green]")
        merge_result = pr.merge(sha=checked_sha, merge_method="squash")
    except GithubException as exc:
        console.print(f"[red]❌ Failed to approve/merge {pr_link}: {exc}[/red]")
        return
    if merge_result.merged:
        console.print(f"[bold green]✅ Successfully merged {pr_link}![/bold green]")
    else:
        console.print(f"[yellow]⚠ Could not merge {pr_link}: {merge_result.message}[/yellow]")


def display_failed_prs(console: Console, failed_prs: list[tuple[str, PullRequest, str, str | None]]) -> None:
    console.print("[bold yellow]⚠️  PRs requiring manual review:[/bold yellow]")
    table: Final = Table(show_header=True)
    table.add_column("Repository", style="cyan")
    table.add_column("PR #", style="magenta")
    table.add_column("Title", style="yellow")
    table.add_column("Reason", style="red")
    for repo_name, pr, reason, reason_url in failed_prs:
        table.add_row(
            repo_name,
            Text(f"#{pr.number}", style=f"link {pr.html_url}"),
            pr.title,
            Text(reason, style=f"link {reason_url or f'{pr.html_url}/checks'}"),
        )
    console.print(table)
    console.print()


def open_failed_prs(console: Console, failed_prs: list[tuple[str, PullRequest, str, str | None]]) -> None:
    console.print("[bold]Opening failed PRs in browser...[/bold]")
    for repo_name, pr, _, _ in failed_prs:
        console.print(f"[dim]Opening {repo_name}#{pr.number}...[/dim]")
        webbrowser.open(pr.html_url)


if __name__ == "__main__":
    main()

__all__ = ["check_pr_status", "display_failed_prs", "display_mergeable_prs", "get_token"]
