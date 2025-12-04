from typing import List, Dict, Tuple
from app.services.patch.utils import split_hunk, computed_hunk_line_number
from app.schemas.gitlab.merge_request_diff import MRDiffItem


class PatchHandler:
    """handle diff content for"""

    def __init__(self, diff_files: List[MRDiffItem]):
        self.extended_diff_files = [
            diff_file for diff_file in diff_files
            if diff_file.diff
        ]

    def get_extended_diff_content(self, commit_message: str) -> str:
        self.extended_lines()
        self.add_line_number()

        extended_diff = f"commit message: {commit_message}\n\n"

        for diff_file in self.extended_diff_files:
            extended_diff += (
                f"## new_path: {diff_file.new_path}\n"
                f"## old_path: {diff_file.old_path}\n"
                f"{diff_file.extended_diff}\n\n"
            )

        return extended_diff

    def extended_lines(self):
        pass

    def add_line_number(self):
        for diff_file in self.extended_diff_files:
            new_diff = ""
            old_lines_with_number: Dict[int, str] = {}
            new_lines_with_number: Dict[int, str] = {}

            hunks = split_hunk(diff_file.diff)

            for hunk in hunks:
                (
                    new_hunk_lines,
                    new_hunk_lines_with_number,
                    old_hunk_lines_with_number
                ) = computed_hunk_line_number(hunk)

                new_diff += "\n".join(new_hunk_lines)

                new_lines_with_number.update(new_hunk_lines_with_number)
                old_lines_with_number.update(old_hunk_lines_with_number)

            diff_file.extended_diff = new_diff
            diff_file.new_lines_with_number = new_lines_with_number
            diff_file.old_lines_with_number = old_lines_with_number

    def get_extended_diff_files(self) -> List[MRDiffItem]:
        return self.extended_diff_files
