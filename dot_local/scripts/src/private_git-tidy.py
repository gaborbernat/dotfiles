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
import subprocess
from argparse import ArgumentParser, Namespace
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from github import Github
from github.Auth import Token
from github.GithubException import GithubException
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from rich.table import Table
from rich_argparse import RichHelpFormatter
from truststore import inject_into_ssl

if TYPE_CHECKING:
    from github.Repository import Repository
    from rich.progress import Progress as ProgressType
    from rich.progress import TaskID


def main() -> None:
    opts = parse_cli()
    console = Console()

    try:
        run(console, opts)
    except KeyboardInterrupt:
        console.print("[red]Interrupted by user (Ctrl+C)[/red]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Git command failed: {e}[/red]")
        raise SystemExit(1) from e


class Options(Namespace):
    dry_run: bool
    verbose: bool
    stale_days: int


def parse_cli() -> Options:
    parser = ArgumentParser(
        description="Clean up Git repository: delete merged branches, sync with upstream, remove stale branches.",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--stale-days",
        type=int,
        default=14,
        help="Days of inactivity before a branch is considered stale (default: 14)",
    )
    opts = Options()
    parser.parse_args(namespace=opts)
    return opts


def get_remote_only_branches(default_branch: str, opts: Options) -> dict[str, list[str]]:
    """Get branches that exist on remotes but not locally."""
    # Get all local branches (%(refname:short) yields clean names, no * / + worktree markers)
    local_output = run_git(["git", "branch", "--format=%(refname:short)"], opts, capture=True)
    local_branches = {b for b in local_output.splitlines() if b}

    # Get all remote branches
    remote_output = run_git(["git", "branch", "-r"], opts, capture=True)
    remote_only: dict[str, list[str]] = {"origin": [], "upstream": []}

    for raw_line in remote_output.strip().split("\n"):
        line = raw_line.strip()
        if not line or "HEAD ->" in line:
            continue

        # Parse remote/branch format
        if "/" not in line:
            continue

        remote, branch = line.split("/", 1)
        if branch in (default_branch, "HEAD"):
            continue

        # Only include if branch doesn't exist locally
        if branch not in local_branches and remote in ("origin", "upstream"):
            remote_only[remote].append(branch)

    return remote_only


def load_all_data(
    console: Console, opts: Options, default_branch: str, github_repo: Repository | None
) -> tuple[list[str], list[str], list[tuple[str, int, str, bool, bool]], dict[str, list[str]]]:
    """Load all branch data upfront to avoid delays during user interaction."""
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Fetching remotes...", total=None)
        run_git(["git", "fetch", "--all", "--prune"], opts)

        progress.update(task, description="Loading branch information...")

        # Get gone branches (upstream tracking deleted); tab-delimited so branch names are safe
        output = run_git(
            ["git", "for-each-ref", "--format=%(refname:short)%09%(upstream:track)", "refs/heads/"],
            opts,
            capture=True,
        )
        gone_branches: list[str] = []
        for line in output.splitlines():
            name, _, track = line.partition("\t")
            if name and "[gone]" in track:
                gone_branches.append(name)

        # Fetch merged-PR head refs once, reused for local and remote-only classification
        merged_pr_refs = find_merged_pr_refs(github_repo, opts, console) if github_repo else {}

        # Get merged branches (name match AND tip SHA match, so a reused branch name is not deleted)
        merged_branches: list[str] = []
        if github_repo:
            progress.update(task, description="Checking for merged PRs...")
            output = run_git(["git", "branch", "--format=%(refname:short)"], opts, capture=True)
            all_branches = [b for b in output.splitlines() if b and b != default_branch]
            merged_branches = [b for b in all_branches if is_ref_merged(b, merged_pr_refs, b, opts)]

        # Get stale branches with all their data (excluding gone and merged branches)
        progress.update(task, description="Analyzing stale branches...")
        stale_branches = get_stale_branches(default_branch, opts.stale_days, opts)
        # Filter out branches that are already gone or merged
        branches_to_exclude = set(gone_branches) | set(merged_branches)
        stale_branches = [(branch, days) for branch, days in stale_branches if branch not in branches_to_exclude]
        stale_branch_data = prepare_stale_branch_data(stale_branches, default_branch, opts, progress, task)

        # Get remote-only branches (on origin/upstream but not local)
        progress.update(task, description="Checking remote-only branches...")
        remote_only_branches = get_remote_only_branches(default_branch, opts)

        # Filter remote-only branches to only include merged ones (verify the remote tip SHA too)
        if github_repo:
            merged_remote_branches: dict[str, list[str]] = {"origin": [], "upstream": []}
            for remote in ("origin", "upstream"):
                merged_remote_branches[remote] = [
                    b for b in remote_only_branches[remote] if is_ref_merged(f"{remote}/{b}", merged_pr_refs, b, opts)
                ]
            remote_only_branches = merged_remote_branches

    return gone_branches, merged_branches, stale_branch_data, remote_only_branches


def run(console: Console, opts: Options) -> None:
    if not run_git(["git", "rev-parse", "--git-dir"], opts, capture=True, check=False).strip():
        console.print("[red]Error: Not a git repository[/red]")
        raise SystemExit(1)

    console.print("[bold cyan]Git Repository Housekeeping[/bold cyan]\n")

    # Get GitHub repo info
    github_repo = get_github_repo(console, opts)

    # Get default branch
    default_branch = get_default_branch(console, opts)
    console.print(f"[dim]Default branch: {default_branch}[/dim]\n")

    # Load ALL data upfront with progress indicator
    gone_branches, merged_branches, stale_branch_data, remote_only_branches = load_all_data(
        console, opts, default_branch, github_repo
    )

    # Show all branches that will be reviewed
    console.print()
    show_branches_to_review(console, gone_branches, merged_branches, stale_branch_data, remote_only_branches)

    # Now do quick user interaction (no delays)
    branches_to_delete = collect_all_deletion_decisions(
        console, opts, default_branch, (gone_branches, merged_branches, stale_branch_data, remote_only_branches)
    )

    if not branches_to_delete:
        console.print("\n[bold green]No branches to delete. Housekeeping complete![/bold green]")
        show_remaining_branches_summary(console, opts, default_branch)
        return

    # Show summary
    show_deletion_summary(console, branches_to_delete)

    # Show what will remain AFTER deletions
    console.print()
    show_remaining_branches_summary(console, opts, default_branch, branches_to_delete)

    if opts.dry_run:
        console.print("\n[dim][DRY RUN] No changes made[/dim]")
        console.print("\n[bold green]Housekeeping complete![/bold green]")
        return

    if not Confirm.ask("\nProceed with deletion?", default=True):
        console.print("[dim]Cancelled[/dim]")
        console.print("\n[bold green]Housekeeping complete![/bold green]")
        return

    # Sync default branch with upstream before deletions
    console.print()
    sync_default_branch(console, opts, default_branch)

    # Batch execute all deletions
    console.print()
    execute_all_deletions(console, opts, default_branch, branches_to_delete)

    console.print("\n[bold green]Housekeeping complete![/bold green]")


def get_github_repo(console: Console, opts: Options) -> Repository | None:
    try:
        # Try upstream first (for forked repos), fall back to origin
        remote_url = run_git(["git", "remote", "get-url", "upstream"], opts, capture=True, check=False).strip()
        if not remote_url:
            remote_url = run_git(["git", "remote", "get-url", "origin"], opts, capture=True).strip()

        # Check for GitHub Enterprise instance (set via GITHUB_ENTERPRISE_HOST env var)
        enterprise_host = os.environ.get("GITHUB_ENTERPRISE_HOST", "")

        # Extract repo path from URL
        # Handle formats like: git@github.com:owner/repo.git or https://github.com/owner/repo.git
        if "github.com" not in remote_url and enterprise_host not in remote_url:
            console.print("[yellow]Warning: Not a GitHub repository, skipping PR merge check[/yellow]")
            return None

        # Extract owner/repo
        if remote_url.startswith("git@"):
            repo_path = remote_url.split(":")[-1].removesuffix(".git")
        else:
            repo_path = "/".join(remote_url.split("/")[-2:]).removesuffix(".git")

        # Determine which GitHub instance to use
        if enterprise_host and enterprise_host in remote_url:
            token = os.environ.get("GITHUB_ENTERPRISE_TOKEN")
            if not token:
                console.print("[yellow]Warning: GITHUB_ENTERPRISE_TOKEN not set, skipping PR merge check[/yellow]")
                return None
            github = Github(base_url=f"https://{enterprise_host}/api/v3", auth=Token(token))
        else:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                console.print("[yellow]Warning: GITHUB_TOKEN not set, skipping PR merge check[/yellow]")
                return None
            inject_into_ssl()
            github = Github(auth=Token(token))

        if opts.verbose:
            console.print(f"[dim]Using GitHub repository: {repo_path}[/dim]")

        return github.get_repo(repo_path)

    except (subprocess.CalledProcessError, GithubException) as e:
        if opts.verbose:
            console.print(f"[yellow]Warning: Could not access GitHub repository: {e}[/yellow]")
        return None


def get_default_branch(console: Console, opts: Options) -> str:
    result = run_git(["git", "symbolic-ref", "refs/remotes/origin/HEAD"], opts, capture=True, check=False).strip()
    if result:
        return result.split("/")[-1]
    console.print("[yellow]Warning: Could not detect default branch, using 'main'[/yellow]")
    return "main"


def sync_default_branch(console: Console, opts: Options, default_branch: str) -> None:
    console.print(f"[bold]Syncing {default_branch} with upstream...[/bold]")

    current_branch = run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], opts, capture=True).strip()
    # A detached HEAD reports "HEAD"; remember the actual commit so we can return to it exactly.
    original_ref = (
        current_branch
        if current_branch != "HEAD"
        else run_git(["git", "rev-parse", "HEAD"], opts, capture=True).strip()
    )
    on_default = current_branch == default_branch

    has_upstream = "upstream" in run_git(["git", "remote"], opts, capture=True).split()
    upstream_ref = f"upstream/{default_branch}" if has_upstream else f"origin/{default_branch}"

    # Stash whenever the tree is dirty (including while already on the default branch).
    stashed = False
    if run_git(["git", "status", "--porcelain"], opts, capture=True).strip():
        console.print("[yellow]Working directory has uncommitted changes, stashing...[/yellow]")
        run_git(["git", "stash", "push", "-u", "-m", "git-tidy auto-stash"], opts)
        stashed = True

    try:
        if not on_default:
            console.print(f"[dim]Switching to {default_branch}[/dim]")
            run_git(["git", "checkout", default_branch], opts)
        _update_default_branch(console, opts, default_branch, upstream_ref)
    finally:
        if not on_default:
            console.print(f"[dim]Switching back to {original_ref}[/dim]")
            run_git(["git", "checkout", original_ref], opts)
        if stashed:
            console.print("[yellow]Restoring stashed changes...[/yellow]")
            if not run_git_ok(["git", "stash", "pop"], opts):
                console.print("[yellow]⚠ Could not pop stash automatically; run 'git stash pop' by hand[/yellow]")

    console.print()


def _update_default_branch(console: Console, opts: Options, default_branch: str, upstream_ref: str) -> None:
    local_commit = run_git(["git", "rev-parse", default_branch], opts, capture=True).strip()
    upstream_commit = run_git(["git", "rev-parse", upstream_ref], opts, capture=True).strip()

    if local_commit == upstream_commit:
        console.print(f"[green]✓ {default_branch} is up to date with {upstream_ref}[/green]")
        return

    merge_base = run_git(["git", "merge-base", default_branch, upstream_ref], opts, capture=True).strip()
    if merge_base == local_commit:
        console.print(f"[yellow]Fast-forwarding {default_branch} to {upstream_ref}[/yellow]")
        run_git(["git", "merge", "--ff-only", upstream_ref], opts)
        console.print(f"[green]✓ {default_branch} fast-forwarded[/green]")
        return

    local_changes = run_git(
        ["git", "log", f"{upstream_ref}..{default_branch}", "--oneline"], opts, capture=True
    ).strip()
    if not local_changes:
        console.print(f"[yellow]Fast-forwarding {default_branch} to {upstream_ref}[/yellow]")
        run_git(["git", "merge", "--ff-only", upstream_ref], opts)
        console.print(f"[green]✓ {default_branch} fast-forwarded[/green]")
        return

    console.print(f"[yellow]Local {default_branch} has diverged from {upstream_ref}[/yellow]")
    if opts.dry_run:
        console.print(f"[dim][DRY RUN] Would rebase {default_branch} onto {upstream_ref}[/dim]")
    elif Confirm.ask(f"Rebase {default_branch} onto {upstream_ref}?"):
        # On a rebase conflict, abort so we never leave a half-finished rebase for the finally block.
        if run_git_ok(["git", "rebase", upstream_ref], opts):
            console.print(f"[green]✓ {default_branch} rebased onto {upstream_ref}[/green]")
        else:
            run_git(["git", "rebase", "--abort"], opts, check=False)
            console.print(f"[red]✗ Rebase hit conflicts; aborted, {default_branch} left unchanged[/red]")


def check_remote_branches(branch: str, opts: Options) -> tuple[bool, bool]:
    origin_result = run_git(["git", "ls-remote", "--heads", "origin", branch], opts, capture=True, check=False).strip()
    has_origin = bool(origin_result)

    upstream_result = run_git(
        ["git", "ls-remote", "--heads", "upstream", branch], opts, capture=True, check=False
    ).strip()
    has_upstream = bool(upstream_result)

    return has_origin, has_upstream


def find_merged_pr_refs(github_repo: Repository, opts: Options, console: Console) -> dict[str, set[str]]:
    """Map each merged PR head-ref name to the set of head SHAs it was merged at (single API pass)."""
    try:
        if opts.verbose:
            console.print(f"[dim]Fetching closed PRs from {github_repo.full_name}...[/dim]")
        refs: dict[str, set[str]] = {}
        count = 0
        for pr in github_repo.get_pulls(state="closed", sort="created", direction="desc"):
            count += 1
            if pr.merged and pr.head and pr.head.ref and pr.head.sha:
                refs.setdefault(pr.head.ref, set()).add(pr.head.sha)
        if opts.verbose:
            console.print(f"[dim]Checked {count} closed PRs; {len(refs)} merged head refs[/dim]")
    except GithubException as e:
        if opts.verbose:
            console.print(f"[yellow]GitHub API error: {e}[/yellow]")
        return {}
    return refs


def is_ref_merged(ref: str, merged_pr_refs: dict[str, set[str]], name: str, opts: Options) -> bool:
    """True only if ``ref``'s tip SHA matches a merged PR that used the branch name ``name``.

    Guards against deleting a branch that merely reuses the name of a historically merged PR: the
    local/remote tip must actually be the SHA that got merged.
    """
    if not (shas := merged_pr_refs.get(name)):
        return False
    tip = run_git(["git", "rev-parse", "--verify", ref], opts, capture=True, check=False).strip()
    return bool(tip) and tip in shas


def switch_if_current_branch(branch: str, default_branch: str, opts: Options, console: Console) -> None:
    if branch == run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], opts, capture=True).strip():
        console.print(f"[yellow]Switching to {default_branch} (current branch will be deleted)[/yellow]")
        run_git(["git", "checkout", default_branch], opts)


def get_stale_branches(default_branch: str, stale_days: int, opts: Options) -> list[tuple[str, int]]:
    output = run_git(
        ["git", "for-each-ref", "--format=%(refname:short)%09%(committerdate:iso8601)", "refs/heads/"],
        opts,
        capture=True,
    )

    stale_branches = []
    cutoff_date = datetime.now(UTC) - timedelta(days=stale_days)

    for line in output.splitlines():
        if "\t" not in line or line.split("\t", 1)[0] == default_branch:
            continue

        branch, date_str = line.split("\t", 1)
        commit_date = datetime.fromisoformat(date_str.replace(" ", "T"))

        if commit_date < cutoff_date:
            days_ago = (datetime.now(UTC) - commit_date).days
            stale_branches.append((branch, days_ago))

    return stale_branches


def delete_branch_and_remotes(
    branch: str, default_branch: str, opts: Options, console: Console, remotes: tuple[bool, bool]
) -> None:
    switch_if_current_branch(branch, default_branch, opts, console)

    run_git(["git", "branch", "-D", branch], opts)
    console.print(f"[green]✓ Deleted local branch {branch}[/green]")

    delete_origin, delete_upstream = remotes

    for remote, wanted in (("origin", delete_origin), ("upstream", delete_upstream)):
        if not wanted:
            continue
        if run_git_ok(["git", "push", remote, "--delete", branch], opts):
            console.print(f"[green]✓ Deleted remote branch {remote}/{branch}[/green]")
        else:
            console.print(f"[yellow]⚠ Could not delete remote branch {remote}/{branch}[/yellow]")


def get_branch_commits(branch: str, default_branch: str, opts: Options) -> str:
    if not (
        merge_base := run_git(["git", "merge-base", default_branch, branch], opts, capture=True, check=False).strip()
    ):
        return ""
    return run_git(
        ["git", "log", "--oneline", "--no-decorate", f"{merge_base}..{branch}", "-15"],
        opts,
        capture=True,
        check=False,
    ).strip()


def prepare_stale_branch_data(
    stale_branches: list[tuple[str, int]],
    default_branch: str,
    opts: Options,
    progress: ProgressType,
    task: TaskID,
) -> list[tuple[str, int, str, bool, bool]]:
    branch_data: list[tuple[str, int, str, bool, bool]] = []
    total = len(stale_branches)
    for idx, (branch, days_ago) in enumerate(sorted(stale_branches, key=lambda x: x[1]), 1):
        progress.update(task, description=f"Analyzing {branch} ({idx}/{total})...")
        commits = get_branch_commits(branch, default_branch, opts)
        has_origin, has_upstream = check_remote_branches(branch, opts)
        branch_data.append((branch, days_ago, commits, has_origin, has_upstream))
    return branch_data


def show_branches_to_review(
    console: Console,
    gone_branches: list[str],
    merged_branches: list[str],
    stale_branch_data: list[tuple[str, int, str, bool, bool]],
    remote_only_branches: dict[str, list[str]],
) -> None:
    """Show a table of all branches that will be reviewed."""
    has_remote_only = any(remote_only_branches.values())
    if not gone_branches and not merged_branches and not stale_branch_data and not has_remote_only:
        return

    console.print("[bold cyan]Branches to review:[/bold cyan]\n")

    table = Table(show_header=True)
    table.add_column("Branch", style="yellow")
    table.add_column("Category", style="cyan")
    table.add_column("Details", style="dim")

    for branch in gone_branches:
        table.add_row(branch, "Gone", "Tracking deleted remote")

    for branch in merged_branches:
        table.add_row(branch, "Merged", "PR has been merged")

    for remote, branches in remote_only_branches.items():
        for branch in branches:
            table.add_row(f"{remote}/{branch}", "Remote-only", f"Merged on {remote}, not local")

    for branch, days_ago, _, _, _ in stale_branch_data:
        table.add_row(branch, "Stale", f"Inactive for {days_ago} days")

    console.print(table)
    console.print()


def collect_gone_branches(
    opts: Options, default_branch: str, gone_branches: list[str]
) -> list[tuple[str, str, bool, bool]]:
    """Collect gone branches whose tips reached the fetched default branch."""
    branches_to_delete: list[tuple[str, str, bool, bool]] = []
    base_ref = f"upstream/{default_branch}"
    if not run_git_ok(["git", "rev-parse", "--verify", base_ref], opts):
        base_ref = default_branch
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {
            executor.submit(run_git_ok, ["git", "merge-base", "--is-ancestor", branch, base_ref], opts): branch
            for branch in gone_branches
        }
        for future in as_completed(futures):
            branch = futures[future]
            if future.result():
                has_origin, has_upstream = check_remote_branches(branch, opts)
                branches_to_delete.append((branch, "gone", has_origin, has_upstream))
    return branches_to_delete


def collect_merged_branches(opts: Options, merged_branches: list[str]) -> list[tuple[str, str, bool, bool]]:
    """Collect merged branches for deletion."""
    branches_to_delete: list[tuple[str, str, bool, bool]] = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = {executor.submit(check_remote_branches, branch, opts): branch for branch in merged_branches}
        for future in as_completed(futures):
            branch = futures[future]
            has_origin, has_upstream = future.result()
            branches_to_delete.append((branch, "merged", has_origin, has_upstream))
    return branches_to_delete


def collect_stale_branches(
    console: Console, opts: Options, stale_branch_data: list[tuple[str, int, str, bool, bool]]
) -> list[tuple[str, str, bool, bool]]:
    """Collect decisions for stale branches."""
    if not stale_branch_data:
        return []

    console.print(
        f"\n[bold yellow]Found {len(stale_branch_data)} stale branches "
        f"(inactive for {opts.stale_days}+ days):[/bold yellow]"
    )
    console.print("[dim]Review each branch:[/dim]\n")

    branches_to_delete: list[tuple[str, str, bool, bool]] = []
    for branch, days_ago, commits, has_origin, has_upstream in stale_branch_data:
        if commits:
            console.print(f"[dim]Recent commits on {branch}:[/dim]")
            for line in commits.split("\n"):
                console.print(f"[dim]  {line}[/dim]")
            console.print()

        if Confirm.ask(f"Delete {branch} (inactive for {days_ago} days)?", default=True):
            branches_to_delete.append((branch, "stale", has_origin, has_upstream))

    return branches_to_delete


def collect_remote_only_branches(remote_only_branches: dict[str, list[str]]) -> list[tuple[str, str, bool, bool]]:
    """Collect remote-only branches for deletion."""
    branches_to_delete: list[tuple[str, str, bool, bool]] = []
    for remote, branches in remote_only_branches.items():
        for branch in branches:
            has_origin = remote == "origin"
            has_upstream = remote == "upstream"
            branches_to_delete.append((branch, "remote-only", has_origin, has_upstream))
    return branches_to_delete


def collect_all_deletion_decisions(
    console: Console,
    opts: Options,
    default_branch: str,
    branch_data: tuple[
        list[str], list[str], list[tuple[str, int, str, bool, bool]], dict[str, list[str]]
    ],  # (gone, merged, stale, remote_only)
) -> list[tuple[str, str, bool, bool]]:
    """Collect all deletion decisions from user. Returns list of (branch, category, has_origin, has_upstream)."""
    gone_branches, merged_branches, stale_branch_data, remote_only_branches = branch_data

    branches_to_delete: list[tuple[str, str, bool, bool]] = []

    branches_to_delete.extend(collect_gone_branches(opts, default_branch, gone_branches))
    branches_to_delete.extend(collect_merged_branches(opts, merged_branches))
    branches_to_delete.extend(collect_remote_only_branches(remote_only_branches))
    branches_to_delete.extend(collect_stale_branches(console, opts, stale_branch_data))

    return branches_to_delete


def show_deletion_summary(console: Console, branches_to_delete: list[tuple[str, str, bool, bool]]) -> None:
    """Show summary of what will be deleted."""
    console.print(f"\n[bold yellow]Will delete {len(branches_to_delete)} branches:[/bold yellow]")

    by_category: dict[str, list[tuple[str, bool, bool]]] = {
        "gone": [],
        "merged": [],
        "remote-only": [],
        "stale": [],
    }
    for branch, category, has_origin, has_upstream in branches_to_delete:
        by_category[category].append((branch, has_origin, has_upstream))

    for category, branches in by_category.items():
        if not branches:
            continue

        console.print(f"\n[cyan]{category.title()} branches ({len(branches)}):[/cyan]")
        for branch, has_origin, has_upstream in branches:
            remotes = [r for r, has in [("origin", has_origin), ("upstream", has_upstream)] if has]
            remote_str = f" + {', '.join(remotes)}" if remotes else ""
            console.print(f"  • {branch}{remote_str}")


def delete_remote_only_branch(branch: str, opts: Options, console: Console, remotes: tuple[bool, bool]) -> None:
    """Delete a branch that only exists on remotes."""
    has_origin, has_upstream = remotes

    for remote, wanted in (("origin", has_origin), ("upstream", has_upstream)):
        if not wanted:
            continue
        if run_git_ok(["git", "push", remote, "--delete", branch], opts):
            console.print(f"[green]✓ Deleted remote branch {remote}/{branch}[/green]")
        else:
            console.print(f"[yellow]⚠ Could not delete remote branch {remote}/{branch}[/yellow]")


def execute_all_deletions(
    console: Console, opts: Options, default_branch: str, branches_to_delete: list[tuple[str, str, bool, bool]]
) -> None:
    """Batch execute all branch deletions."""
    console.print("\n[bold]Deleting branches...[/bold]")

    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        task = progress.add_task("Deleting branches...", total=len(branches_to_delete))

        for branch, category, has_origin, has_upstream in branches_to_delete:
            progress.update(task, description=f"Deleting {branch}...")
            if category == "remote-only":
                delete_remote_only_branch(branch, opts, console, (has_origin, has_upstream))
            else:
                delete_branch_and_remotes(branch, default_branch, opts, console, (has_origin, has_upstream))
            progress.advance(task)


def show_remaining_branches_summary(
    console: Console,
    opts: Options,
    default_branch: str,
    branches_to_delete: list[tuple[str, str, bool, bool]] | None = None,
) -> None:
    console.print("\n[bold]Remaining branches:[/bold]")

    branches_to_exclude = {default_branch, "dependyfriend-updates"}
    if branches_to_delete:
        branches_to_exclude.update(branch for branch, _, _, _ in branches_to_delete)

    output = run_git(
        [
            "git",
            "for-each-ref",
            "--format=%(refname:short)%09%(committerdate:relative)%09%(subject)",
            "--sort=-committerdate",
            "refs/heads/",
        ],
        opts,
        capture=True,
    )

    table = Table(show_header=True)
    table.add_column("Branch", style="cyan")
    table.add_column("Last Commit", style="yellow")
    table.add_column("Message", style="dim")

    current_branch = run_git(["git", "rev-parse", "--abbrev-ref", "HEAD"], opts, capture=True).strip()

    for line in output.splitlines():
        if not line or "\t" not in line:
            continue

        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue

        branch, when, message = parts

        if branch in branches_to_exclude:
            continue

        branch_display = f"* {branch}" if branch == current_branch else f"  {branch}"
        table.add_row(branch_display, when, message)

    console.print(table)


_READONLY_GIT = frozenset({"rev-parse", "symbolic-ref", "remote", "for-each-ref", "ls-remote", "log", "merge-base"})
_BRANCH_MUTATORS = frozenset({"-d", "-D", "--delete", "-m", "-M", "--move", "-c", "-C", "--copy"})


def _is_readonly_git(cmd: list[str]) -> bool:
    if cmd[1] in _READONLY_GIT:
        return True
    # `git branch` lists (read) unless a mutating flag is present
    return cmd[1] == "branch" and _BRANCH_MUTATORS.isdisjoint(cmd[2:])


def run_git(cmd: list[str], opts: Options, *, capture: bool = False, check: bool = True) -> str:
    if opts.dry_run and not capture and not _is_readonly_git(cmd):
        return ""

    result = subprocess.run(cmd, capture_output=True, text=True, check=check)

    if capture:
        return result.stdout

    return ""


def run_git_ok(cmd: list[str], opts: Options) -> bool:
    """Run a mutating git command, returning whether it succeeded (True in dry-run)."""
    if opts.dry_run:
        return True
    return subprocess.run(cmd, capture_output=True, text=True, check=False).returncode == 0


if __name__ == "__main__":
    main()
