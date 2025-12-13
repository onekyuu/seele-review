import httpx
from typing import Optional, List, Dict, Any, Literal

from app.schemas.agent.review import Review
from app.schemas.gitlab.merge_request_object import MRObj
from app.schemas.gitlab.merge_request_diff import MRDiffItem
from app.services.notification import SlackNotifier


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


class GitlabPublishService:
    """GitLab publish service class"""

    def __init__(self, gitlab_api_base: str, gitlab_token: str, bot_name: str = "🤖 AI Review Bot"):
        """Initialize GitLab publish service

        Args:
            gitlab_api_base: GitLab API base URL
            gitlab_token: GitLab API token
            bot_name: Bot display name in comments
        """
        self.gitlab_api_base = gitlab_api_base.rstrip('/')
        self.gitlab_token = gitlab_token
        self.bot_name = bot_name
        self.headers = {'PRIVATE-TOKEN': gitlab_token}
        self.slack_notifier = SlackNotifier()

    async def publish(
        self,
        mode: Literal['report', 'comment'],
        reviews: List[Review],
        mr_obj: MRObj,
        diff_items: List[MRDiffItem],
        project_id: int,
        mr_iid: int,
        callback: Optional[Dict[str, Any]] = None,
    ):
        """Publish code review results

        Args:
            mode: Publish mode ('report' or 'comment')
            reviews: List of review results
            mr_obj: Merge request object
            diff_items: List of diff items
            project_id: GitLab project ID
            mr_iid: Merge request IID
            callback: Optional callback parameters for notification
        """
        if mode == 'comment':
            # Comment mode: Publish comment on each line of code
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

                await self._publish_line_comment(
                    project_id,
                    mr_iid,
                    new_path,
                    old_path,
                    end_line,
                    issue_content_markdown,
                    review_type,
                    mr_obj
                )

        else:
            # Report mode: Publish summary report
            web_url = mr_obj.web_url
            source_branch = mr_obj.source_branch
            target_branch = mr_obj.target_branch

            issue_content_markdown = ''

            for review in reviews:
                new_path = review.new_path
                old_path = review.old_path
                review_type = review.type
                start_line = review.start_line
                end_line = review.end_line
                issue_content = review.issue_content
                issue_header = review.issue_header

                # Find corresponding diff item
                diff_item = next(
                    (item for item in diff_items if item.new_path == new_path),
                    None
                )

                diff_code = self._get_diff_code(
                    diff_item, review_type, start_line, end_line)

                # Build code link
                if review_type == 'new':
                    code_url = (
                        f'[Lines {start_line} to {end_line} in {new_path}]'
                        f'({web_url}/-/blob/{source_branch}/{new_path}?ref_type=heads#L{start_line}-{end_line})\n'
                        f'<details><summary>diff</summary>\n\n```diff\n{diff_code}\n```\n\n</details>'
                    )
                else:
                    code_url = (
                        f'[Lines {start_line} to {end_line} in {old_path}]'
                        f'({web_url}/-/blob/{target_branch}/{old_path}?ref_type=heads#L{start_line}-{end_line})\n'
                        f'<details><summary>diff</summary>\n\n```diff\n{diff_code}\n```\n\n</details>'
                    )

                issue_content_markdown += (
                    ISSUE_REPORT_MARKDOWN_TEMPLATE
                    .replace('__issue_header__', issue_header)
                    .replace('__issue_code_url__', code_url)
                    .replace('__issue_content__', issue_content)
                ) + '\n'

            # Publish summary comment
            await self._publish_general_comment(
                project_id,
                mr_iid,
                f'## Issue List\n'
                f'<table>\n'
                f'  <thead><tr><td><strong>Issue</strong></td><td><strong>Code Location</strong></td>'
                f'<td><strong>Description</strong></td></tr></thead>\n'
                f'  <tbody>\n{issue_content_markdown}\n</tbody>\n</table>'
            )

        # Send notification if callback provided
        if callback:
            self.slack_notifier.send_review_notification(
                push_url=callback.get('push_url', ''),
                user_name=callback.get('user_name', ''),
                project_name=callback.get('project_name', ''),
                source_branch=mr_obj.source_branch,
                target_branch=mr_obj.target_branch,
                content=callback.get('content', ''),
                mr_url=callback.get('mr_url', ''),
                mr_title=callback.get('mr_title', ''),
                reviews_count=len(reviews),
            )

    async def _publish_line_comment(
        self,
        project_id: int,
        mr_iid: int,
        new_path: str,
        old_path: str,
        line: int,
        content: str,
        line_type: Literal['new', 'old'],
        mr_obj: MRObj
    ):
        """Publish comment on specific line"""
        # Add bot signature to content
        formatted_content = f"{self.bot_name}\n\n{content}"

        async with httpx.AsyncClient(timeout=30) as client:
            discussion_data = {
                'body': formatted_content,
                'position': {
                    'position_type': 'text',
                    'new_path': new_path,
                    'old_path': old_path,
                    'new_line': line if line_type == 'new' else None,
                    'old_line': line if line_type == 'old' else None,
                    'base_sha': mr_obj.diff_refs.base_sha,
                    'start_sha': mr_obj.diff_refs.start_sha,
                    'head_sha': mr_obj.diff_refs.head_sha,
                }
            }

            response = await client.post(
                f'{self.gitlab_api_base}/projects/{project_id}/merge_requests/{mr_iid}/discussions',
                headers=self.headers,
                json=discussion_data
            )
            response.raise_for_status()
            return response.json()

    async def _publish_general_comment(
        self,
        project_id: int,
        mr_iid: int,
        content: str
    ):
        """Publish general comment on merge request"""
        # Add bot signature to content
        formatted_content = f"{self.bot_name}\n\n{content}"

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f'{self.gitlab_api_base}/projects/{project_id}/merge_requests/{mr_iid}/notes',
                headers=self.headers,
                json={'body': formatted_content}
            )
            response.raise_for_status()
            return response.json().get('id')

    def _get_diff_code(
        self,
        diff_item: Optional[MRDiffItem],
        review_type: Literal['new', 'old'],
        start_line: int,
        end_line: int
    ) -> str:
        """Get diff code snippet"""
        if not diff_item or not diff_item.diff:
            return ''

        diff_lines = diff_item.diff.split('\n')
        result_lines = []
        current_old_line = 0
        current_new_line = 0

        # Parse diff headers to get starting line numbers
        for line in diff_lines:
            if line.startswith('@@'):
                # Extract line numbers from @@ -old_start,old_count +new_start,new_count @@
                parts = line.split('@@')[1].strip().split()
                if len(parts) >= 2:
                    old_start = int(parts[0].split(',')[0][1:])
                    new_start = int(parts[1].split(',')[0][1:])
                    current_old_line = old_start
                    current_new_line = new_start
                break

        # Collect lines within range with context
        context_before = 3
        context_after = 3
        target_start = start_line - context_before
        target_end = end_line + context_after

        for line in diff_lines:
            if line.startswith('@@'):
                continue

            line_num = current_new_line if review_type == 'new' else current_old_line

            if target_start <= line_num <= target_end:
                result_lines.append(line)

            # Update line counters
            if line.startswith('+'):
                current_new_line += 1
            elif line.startswith('-'):
                current_old_line += 1
            else:
                current_old_line += 1
                current_new_line += 1

        return '\n'.join(result_lines)
