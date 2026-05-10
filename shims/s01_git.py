import logging

logger = logging.getLogger(__name__)

from typing import List, Dict, Any, Tuple
from core.registry import register_shim
from core.errors import ShimError
from shims import BaseShim


@register_shim("git")
class GitShim(BaseShim):
    """
    In-memory high-fidelity Git repository simulator.
    Tracks branches, commits, PRs, and file-level diffs.
    """

    @property
    def name(self) -> str:
        return "git"

    @property
    def description(self) -> str:
        return (
            "Enterprise version control system for managing code and document history."
        )

    def reset(self) -> None:
        """Deterministic reset of the git environment."""
        self._state["repos"]: Dict[str, Any] = {
            "main": {
                "branches": ["main", "dev"],
                "current_branch": "main",
                "commits": [
                    {
                        "hash": "initial",
                        "message": "Initial commit",
                        "files": {"README.md": "# Project Root\n"},
                    }
                ],
                "files": {"README.md": "# Project Root\n"},
                "prs": [],
            }
        }

    def clone(self, repo_url: str) -> str:
        """Simulates cloning a repository."""
        if "main" in repo_url:
            return "Cloned repository 'main' to local workspace."
        raise ShimError(f"Repository URL '{repo_url}' not found.")

    def commit(self, repo: str, files: Dict[str, str], message: str) -> str:
        """Creates a new commit in the current branch."""
        if repo not in self._state["repos"]:
            raise ShimError(f"Repo '{repo}' not found.")

        repo_data = self._state["repos"][repo]
        new_commit = {
            "hash": f"commit_{len(repo_data['commits'])}",
            "message": message,
            "files": files.copy(),
        }
        repo_data["commits"].append(new_commit)
        repo_data["files"].update(files)
        return f"Committed as {new_commit['hash']}."

    def push(self, repo: str, branch: str) -> str:
        """Simulates pushing local changes to a remote branch."""
        return f"Successfully pushed changes to remote branch '{branch}' in repository '{repo}'."

    def create_pr(self, repo: str, source: str, target: str, title: str) -> str:
        """Creates a pull request between two branches."""
        if repo not in self._state["repos"]:
            raise ShimError(f"Repo '{repo}' not found.")

        pr_id = f"PR-{len(self._state['repos'][repo]['prs']) + 1}"
        self._state["repos"][repo]["prs"].append(
            {
                "id": pr_id,
                "source": source,
                "target": target,
                "title": title,
                "status": "OPEN",
            }
        )
        return pr_id

    def get_diff(self, repo: str, commit_a: str, commit_b: str) -> str:
        """Simulates getting a diff between two commits."""
        return f"--- a/README.md\n+++ b/README.md\n@@ -1 +1,2 @@\n # Project Root\n+New changes added in {commit_b}."

    def list_branches(self, repo: str) -> List[str]:
        """Lists all branches in the repository."""
        if repo not in self._state["repos"]:
            raise ShimError(f"Repo '{repo}' not found.")
        return self._state["repos"][repo]["branches"]

    def get_tool_specs(self) -> List[Tuple[str, Any, str]]:
        return [
            ("git_clone", self.clone, "Clone an enterprise repository."),
            ("git_commit", self.commit, "Commit changes to the current branch."),
            ("git_push", self.push, "Push local changes to a remote repository."),
            ("git_create_pr", self.create_pr, "Create a pull request for code review."),
            ("git_get_diff", self.get_diff, "Get the diff between two commits."),
            (
                "git_list_branches",
                self.list_branches,
                "List all branches in a repository.",
            ),
        ]
