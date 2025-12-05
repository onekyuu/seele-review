import hashlib
import hmac
from typing import Optional, Tuple

import httpx

from app.config import settings
from app.schemas.github.pull_request_object import PRObj
from app.schemas.github.pull_request_diff import GithubDiffItem


class GithubApiError(Exception):
    """GitHub API error"""


class GithubClient:
    """GitHub API client"""

    def __init__(self, api_base: str):
        self.api_base = api_base.rstrip('/')
        self.headers = {
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }

    def _verify_github_signature(self, signature: Optional[str], payload: bytes):
        """Verify GitHub webhook signature

        Args:
            signature: X-Hub-Signature-256 header value
            payload: Request body bytes

        Raises:
            GithubApiError: If signature verification fails
        """
        if not signature:
            raise GithubApiError("Missing X-Hub-Signature-256 header")

        if not settings.github_webhook_secret:
            print(
                "[WARNING] GitHub webhook secret not configured, skipping verification")
            return

        # Compute expected signature
        expected_signature = 'sha256=' + hmac.new(
            str(settings.github_webhook_secret).encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()

        # Compare signatures
        if not hmac.compare_digest(signature, expected_signature):
            raise GithubApiError("Invalid GitHub webhook signature")

    async def _get_github_pr_diff(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        api_token: Optional[str] = None
    ) -> Tuple[list, PRObj]:
        """Get GitHub pull request diff and metadata

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            api_token: GitHub personal access token

        Returns:
            Tuple of (diff_items, pr_obj)

        Raises:
            GithubApiError: If API request fails
        """
        headers = self.headers.copy()
        if api_token:
            if api_token.startswith('ghp_') or api_token.startswith('github_pat_'):
                headers['Authorization'] = f'token {api_token}'
            else:
                headers['Authorization'] = f'Bearer {api_token}'

        print(f"[DEBUG] Fetching PR: {owner}/{repo}#{pr_number}")

        async with httpx.AsyncClient(timeout=30) as client:
            # Get PR metadata
            pr_url = f'{self.api_base}/repos/{owner}/{repo}/pulls/{pr_number}'
            print(f"[DEBUG] PR URL: {pr_url}")

            try:
                pr_response = await client.get(pr_url, headers=headers)
                print(f"[DEBUG] PR response status: {pr_response.status_code}")
                pr_response.raise_for_status()
                pr_data = pr_response.json()
                print(
                    f"[DEBUG] PR fetched successfully: {pr_data.get('title')}")
            except httpx.HTTPStatusError as e:
                print(f"[ERROR] HTTP error: {e.response.status_code}")
                print(f"[ERROR] Response: {e.response.text}")
                raise GithubApiError(
                    f"Failed to fetch PR metadata: {e.response.status_code} {e.response.text}"
                ) from e
            except Exception as e:
                print(f"[ERROR] Unexpected error: {str(e)}")
                raise GithubApiError(
                    f"Failed to fetch PR metadata: {str(e)}") from e

            # Get PR files (diff)
            files_url = f'{self.api_base}/repos/{owner}/{repo}/pulls/{pr_number}/files'
            try:
                files_response = await client.get(files_url, headers=headers)
                files_response.raise_for_status()
                files_data = files_response.json()
                print(f"[DEBUG] Fetched {len(files_data)} files")
            except httpx.HTTPStatusError as e:
                raise GithubApiError(
                    f"Failed to fetch PR files: {e.response.status_code} {e.response.text}"
                )
            except Exception as e:
                raise GithubApiError(f"Failed to fetch PR files: {str(e)}")

            # Parse PR object
            pr_obj = PRObj(
                id=pr_data['id'],
                number=pr_data['number'],
                title=pr_data['title'],
                body=pr_data.get('body', ''),
                state=pr_data['state'],
                html_url=pr_data['html_url'],
                diff_url=pr_data['diff_url'],
                user=pr_data['user'],
                created_at=pr_data['created_at'],
                updated_at=pr_data['updated_at'],
                head=pr_data['head'],
                base=pr_data['base'],
            )

            # Convert files to diff items using GitHub model
            diff_items = []

            for file in files_data:
                # Get the patch (diff content) for this file
                patch = file.get('patch', '')

                diff_item = GithubDiffItem(
                    diff=patch,
                    new_path=file['filename'],
                    old_path=file.get('previous_filename', file['filename']),
                    new_file=file['status'] == 'added',
                    renamed_file=file['status'] == 'renamed',
                    deleted_file=file['status'] == 'removed',
                )
                diff_items.append(diff_item)

            return diff_items, pr_obj

    async def create_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_id: str,
        path: str,
        line: int,
        body: str,
        api_token: str
    ):
        """Create a review comment on a specific line"""
        headers = self.headers.copy()
        if api_token.startswith('ghp_') or api_token.startswith('github_pat_'):
            headers['Authorization'] = f'token {api_token}'
        else:
            headers['Authorization'] = f'Bearer {api_token}'

        url = f'{self.api_base}/repos/{owner}/{repo}/pulls/{pr_number}/comments'

        data = {
            'body': body,
            'commit_id': commit_id,
            'path': path,
            'line': line,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise GithubApiError(
                    f"Failed to create review comment: {e.response.status_code} {e.response.text}"
                )
            except Exception as e:
                raise GithubApiError(
                    f"Failed to create review comment: {str(e)}")

    async def create_issue_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
        api_token: str
    ):
        """Create a general comment on the pull request"""
        headers = self.headers.copy()
        if api_token.startswith('ghp_') or api_token.startswith('github_pat_'):
            headers['Authorization'] = f'token {api_token}'
        else:
            headers['Authorization'] = f'Bearer {api_token}'

        url = f'{self.api_base}/repos/{owner}/{repo}/issues/{pr_number}/comments'

        data = {'body': body}

        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.post(url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                raise GithubApiError(
                    f"Failed to create issue comment: {e.response.status_code} {e.response.text}"
                )
            except Exception as e:
                raise GithubApiError(
                    f"Failed to create issue comment: {str(e)}")
