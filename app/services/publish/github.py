from typing import Optional, List, Dict, Any, Literal
import httpx

from app.schemas.agent.review import Review
from app.schemas.github.pull_request_object import PRObj
from app.schemas.gitlab.merge_request_diff import MRDiffItem

ISSUE_COMMENT_MARKDOWN_TEMPLATE = (
    '<table><thead><tr><td><strong>Issue</strong></td><td><strong>Description</strong></td></tr></thead>'
    '<tbody><tr><td>__issue_header__</td><td>__issue_content__</td></tr></tbody></table>'
)

ISSUE_REPORT_MARKDOWN_TEMPLATE = (
    '<tr>\n'
    '  <td>__issue_header__</td>\n'
    '  <td>__issue_code_url__</td>\n'
    '  <td>__issue_content__</td>\n'
    '</tr>'
)


class GithubPublishService:
    """GitHub publish service class"""

    def __init__(self, github_api_base: str, github_token: str, bot_name: str = "🤖 AI Review Bot"):
        """Initialize GitHub publish service

        Args:
            github_api_base: GitHub API base URL
            github_token: GitHub API token
            bot_name: Bot display name in comments
        """
        self.github_api_base = github_api_base.rstrip('/')
        self.github_token = github_token
        self.bot_name = bot_name
        self.headers = {
            'Authorization': f'Bearer {github_token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }

    async def publish(
        self,
        mode: Literal['report', 'comment'],
        reviews: List[Review],
        pr_obj: PRObj,
        diff_items: List[MRDiffItem],
        owner: str,
        repo: str,
        pr_number: int,
        callback: Optional[Dict[str, Any]] = None,
    ):
        """Publish reviews to GitHub PR

        Args:
            mode: Review mode (comment/report)
            reviews: List of reviews
            pr_obj: Pull request object
            diff_items: List of diff items
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            callback: Optional callback data for notifications
        """
        if mode == 'comment':
            await self._publish_comments(
                reviews, pr_obj, diff_items, owner, repo, pr_number
            )
        else:
            await self._publish_report(
                reviews, pr_obj, diff_items, owner, repo, pr_number
            )

        # Send notification if callback provided
        if callback and callback.get('push_url'):
            await self._send_notification(callback, len(reviews))

    async def _publish_comments(
        self,
        reviews: List[Review],
        pr_obj: PRObj,
        diff_items: List[MRDiffItem],
        owner: str,
        repo: str,
        pr_number: int
    ):
        """Publish reviews as line comments"""
        commit_id = pr_obj.head['sha']

        for review in reviews:
            new_path = review.new_path
            old_path = review.old_path
            review_type = review.type
            end_line = review.end_line
            issue_content = review.issue_content
            issue_header = review.issue_header

            issue_content_markdown = (
                ISSUE_COMMENT_MARKDOWN_TEMPLATE
                .replace('__issue_header__', issue_header)
                .replace('__issue_content__', issue_content)
            )

            # Add bot signature
            formatted_content = f"{self.bot_name}\n\n{issue_content_markdown}"

            # Find matching diff item
            diff_item = None
            for item in diff_items:
                if item.new_path == new_path or item.old_path == old_path:
                    diff_item = item
                    break

            if not diff_item:
                print(f"[WARNING] Diff item not found for {new_path}, skipping comment")
                continue

            try:
                # Determine the correct line and side based on review type
                if review_type == 'new':
                    # Comment on new file (right side)
                    await self._publish_review_comment(
                        owner=owner,
                        repo=repo,
                        pr_number=pr_number,
                        commit_id=commit_id,
                        path=new_path,
                        line=end_line,
                        body=formatted_content,
                        side='RIGHT'
                    )
                else:
                    # Comment on old file (left side)
                    await self._publish_review_comment(
                        owner=owner,
                        repo=repo,
                        pr_number=pr_number,
                        commit_id=commit_id,
                        path=new_path,
                        line=end_line,
                        body=formatted_content,
                        side='LEFT'
                    )

                print(f"[SUCCESS] Published comment on {new_path}:{end_line}")

            except Exception as e:
                print(f"[ERROR] Failed to publish comment on {new_path}:{end_line}: {e}")
                # Continue with next review even if one fails
                continue

    async def _publish_report(
        self,
        reviews: List[Review],
        pr_obj: PRObj,
        diff_items: List[MRDiffItem],
        owner: str,
        repo: str,
        pr_number: int
    ):
        """Publish reviews as a summary report"""
        if not reviews:
            return

        # Build report table
        report_rows = []
        for review in reviews:
            new_path = review.new_path
            end_line = review.end_line
            issue_header = review.issue_header
            issue_content = review.issue_content

            # Create link to code location
            code_url = f"{pr_obj.html_url}/files#diff-{self._get_file_anchor(new_path)}R{end_line}"

            report_row = (
                ISSUE_REPORT_MARKDOWN_TEMPLATE
                .replace('__issue_header__', issue_header)
                .replace('__issue_code_url__', f'[{new_path}:{end_line}]({code_url})')
                .replace('__issue_content__', issue_content)
            )
            report_rows.append(report_row)

        # Build complete report
        report_content = f"""
{self.bot_name}

## Code Review Report

<table>
<thead>
<tr>
<th>Issue</th>
<th>Location</th>
<th>Description</th>
</tr>
</thead>
<tbody>
{''.join(report_rows)}
</tbody>
</table>

**Total Issues Found:** {len(reviews)}
"""

        try:
            await self._publish_issue_comment(
                owner=owner,
                repo=repo,
                pr_number=pr_number,
                body=report_content
            )
            print(f"[SUCCESS] Published report with {len(reviews)} issues")

        except Exception as e:
            print(f"[ERROR] Failed to publish report: {e}")
            raise

    async def _publish_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_id: str,
        path: str,
        line: int,
        body: str,
        side: Literal['LEFT', 'RIGHT'] = 'RIGHT'
    ):
        """Publish comment on specific line

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            commit_id: SHA of the commit
            path: File path
            line: Line number
            body: Comment body
            side: Which side of the diff (LEFT for old, RIGHT for new)
        """
        url = f'{self.github_api_base}/repos/{owner}/{repo}/pulls/{pr_number}/comments'

        data = {
            'body': body,
            'commit_id': commit_id,
            'path': path,
            'line': line,
            'side': side,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()

    async def _publish_issue_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str
    ):
        """Publish general comment on pull request

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            body: Comment body
        """
        url = f'{self.github_api_base}/repos/{owner}/{repo}/issues/{pr_number}/comments'

        data = {'body': body}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=self.headers, json=data)
            response.raise_for_status()
            return response.json()

    def _get_file_anchor(self, file_path: str) -> str:
        """Generate GitHub file anchor for linking

        Args:
            file_path: File path

        Returns:
            Anchor string for URL
        """
        # GitHub uses a hash of the file path for anchors
        # This is a simplified version - actual implementation may vary
        import hashlib
        return hashlib.md5(file_path.encode()).hexdigest()[:8]

    async def _send_notification(self, callback: Dict[str, Any], review_count: int):
        """Send notification to external webhook

        Args:
            callback: Callback data including push_url
            review_count: Number of reviews published
        """
        push_url = callback.get('push_url')
        if not push_url:
            return

        notification_data = {
            'msg_type': 'text',
            'content': {
                'text': (
                    f"🤖 AI Code Review Completed\n\n"
                    f"Project: {callback.get('project_name', 'Unknown')}\n"
                    f"PR: {callback.get('pr_title', 'Unknown')}\n"
                    f"Author: {callback.get('user_name', 'Unknown')}\n"
                    f"Issues Found: {review_count}\n"
                    f"Link: {callback.get('pr_url', '')}"
                )
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(push_url, json=notification_data)
                response.raise_for_status()
                print(f"[SUCCESS] Notification sent to {push_url}")
        except Exception as e:
            print(f"[ERROR] Failed to send notification: {e}")
            # Don't raise - notification failure shouldn't fail the whole process