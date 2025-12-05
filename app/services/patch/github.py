from typing import List
from app.constants import CODE_EXTENSIONS, EXCLUDE_EXTENSIONS
from app.schemas.github.pull_request_diff import GithubDiffItem


class GithubPatchHandler:
    """GitHub Patch Handler for processing diff items"""

    def __init__(self, diff_items: List[GithubDiffItem]):
        """
        Initialize handler with GitHub diff items

        Args:
            diff_items: List of GithubDiffItem objects
        """
        self.diff_items = diff_items

    def get_diff_items(self) -> List[GithubDiffItem]:
        """
        Get the list of diff items

        Returns:
            List of GithubDiffItem objects
        """
        return self.diff_items

    def get_extended_diff_content(self, commit_message: str = "") -> str:
        """
        Generate extended diff content for AI analysis

        Args:
            commit_message: The commit or PR title message

        Returns:
            Formatted diff string with file headers and changes
        """
        extended_diff_lines = []

        # Add commit message header if provided
        if commit_message:
            extended_diff_lines.append(f"Commit Message: {commit_message}")
            extended_diff_lines.append("")

        for item in self.diff_items:
            # Skip deleted files or files without diff content
            if item.deleted_file or not item.diff:
                continue

            # Skip files that are too large or collapsed
            if item.too_large or item.collapsed:
                continue

            # Add file header
            if item.new_file:
                extended_diff_lines.append(f"--- /dev/null")
                extended_diff_lines.append(f"+++ b/{item.new_path}")
            elif item.renamed_file:
                extended_diff_lines.append(f"--- a/{item.old_path}")
                extended_diff_lines.append(f"+++ b/{item.new_path}")
            else:
                extended_diff_lines.append(f"--- a/{item.old_path}")
                extended_diff_lines.append(f"+++ b/{item.new_path}")

            # Add the actual diff content
            extended_diff_lines.append(item.diff)
            extended_diff_lines.append("")  # Empty line between files

        return "\n".join(extended_diff_lines)

    def filter_code_files(self) -> List[GithubDiffItem]:
        """
        Filter out non-code files (images, binaries, etc.)

        Returns:
            List of code file diff items
        """

        filtered_items = []
        for item in self.diff_items:
            # Skip deleted files
            if item.deleted_file:
                continue

            # Get file extension
            file_ext = None
            if '.' in item.new_path:
                file_ext = '.' + item.new_path.rsplit('.', 1)[-1].lower()

            # Skip if explicitly excluded
            if file_ext in EXCLUDE_EXTENSIONS:
                continue

            # Skip if too large or collapsed
            if item.too_large or item.collapsed:
                continue

            # Skip generated files
            if item.generated_file:
                continue

            # Include if it's a known code extension or has diff content
            if file_ext in CODE_EXTENSIONS or (item.diff and len(item.diff) > 0):
                filtered_items.append(item)

        return filtered_items

    def get_file_changes_summary(self) -> dict:
        """
        Get a summary of file changes

        Returns:
            Dictionary with change statistics
        """
        summary = {
            'total_files': len(self.diff_items),
            'new_files': 0,
            'modified_files': 0,
            'deleted_files': 0,
            'renamed_files': 0,
        }

        for item in self.diff_items:
            if item.new_file:
                summary['new_files'] += 1
            elif item.deleted_file:
                summary['deleted_files'] += 1
            elif item.renamed_file:
                summary['renamed_files'] += 1
            else:
                summary['modified_files'] += 1

        return summary

    def has_code_changes(self) -> bool:
        """
        Check if there are any code file changes

        Returns:
            True if there are code changes, False otherwise
        """
        code_files = self.filter_code_files()
        return len(code_files) > 0
