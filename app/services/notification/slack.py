"""Slack webhook notification service"""
import httpx
from typing import Optional


class SlackNotifier:
    """Slack webhook notification service"""

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Slack notifier

        Args:
            webhook_url: Slack webhook URL
        """
        self.webhook_url = webhook_url

    def send_review_notification(
        self,
        user_name: str,
        project_name: str,
        source_branch: str,
        target_branch: str,
        content: str = "",
        mr_url: str = "",
        mr_title: str = "",
        reviews_count: int = 0,
        push_url: Optional[str] = None,
    ) -> bool:
        """
        Send code review completion notification to Slack

        Args:
            user_name: User who created the MR
            project_name: Project name
            source_branch: Source branch name
            target_branch: Target branch name
            content: Additional content
            mr_url: MR web URL
            mr_title: MR title
            reviews_count: Number of reviews
            push_url: Override webhook URL

        Returns:
            True if successful, False otherwise
        """
        webhook = push_url or self.webhook_url

        if not webhook:
            print("[WARNING] Slack webhook URL not configured, skipping notification")
            return False

        # Determine icon and result text
        if reviews_count == 0:
            icon = "✅"
            result_text = "No issues found"
        else:
            icon = "📝"
            result_text = f"{reviews_count} review comment{'s' if reviews_count > 1 else ''}"

        # Build MR link
        if mr_url and mr_title:
            mr_link = f"<{mr_url}|{mr_title}>"
        elif mr_url:
            mr_link = f"<{mr_url}|View MR>"
        else:
            mr_link = "N/A"

        # Build message
        message = (
            f"{icon} *AI Code Review Completed*\n\n"
            f"*Project:* {project_name}\n"
            f"*MR:* {mr_link}\n"
            f"*Author:* {user_name}\n"
            f"*Branch:* `{source_branch}` → `{target_branch}`\n"
            f"*Result:* {result_text}"
        )

        if content:
            message += f"\n\n{content}"

        payload = {
            'text': message
        }

        print(f"[INFO] Sending Slack notification to {webhook}")
        print(f"[DEBUG] Payload: {payload}")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(webhook, json=payload)

                if response.status_code == 200:
                    print('[SUCCESS] Slack notification sent')
                    print(f'[DEBUG] Response: {response.text}')
                    return True
                else:
                    print(
                        f'[ERROR] Slack notification failed: {response.status_code}')
                    print(f'[DEBUG] Response body: {response.text}')
                    return False

        except Exception as e:
            print(f'[ERROR] Failed to send Slack notification: {str(e)}')
            import traceback
            traceback.print_exc()
            return False

    def send_error_notification(
        self,
        project_name: str,
        mr_title: str,
        mr_url: str,
        error_message: str,
        push_url: Optional[str] = None,
    ) -> bool:
        """
        Send error notification to Slack

        Args:
            project_name: Project name
            mr_title: MR title
            mr_url: MR web URL
            error_message: Error message
            push_url: Override webhook URL

        Returns:
            True if successful, False otherwise
        """
        webhook = push_url or self.webhook_url

        if not webhook:
            return False

        # Build MR link
        if mr_url and mr_title:
            mr_link = f"<{mr_url}|{mr_title}>"
        elif mr_url:
            mr_link = f"<{mr_url}|View MR>"
        else:
            mr_link = mr_title

        message = (
            f"❌ *AI Code Review Failed*\n\n"
            f"*Project:* {project_name}\n"
            f"*MR:* {mr_link}\n"
            f"*Error:* {error_message}"
        )

        payload = {
            'text': message
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(webhook, json=payload)
                return response.status_code == 200

        except Exception as e:
            print(f'[ERROR] Failed to send Slack error notification: {str(e)}')
            return False
