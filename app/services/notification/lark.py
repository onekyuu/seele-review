"""Lark (Feishu) webhook notification service"""
import httpx
from typing import Optional


class LarkNotifier:
    """Lark (Feishu) webhook notification service"""

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Lark notifier

        Args:
            webhook_url: Lark webhook URL
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
        Send code review completion notification to Lark

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
            print("[WARNING] Lark webhook URL not configured, skipping notification")
            return False

        # Determine icon and result text
        if reviews_count == 0:
            icon = "✅"
            result_text = "No issues found"
            color = "green"
        else:
            icon = "📝"
            result_text = f"{reviews_count} review comment{'s' if reviews_count > 1 else ''}"
            color = "orange"

        # Build MR link
        if mr_url and mr_title:
            mr_link = f"[{mr_title}]({mr_url})"
        elif mr_url:
            mr_link = f"[View MR]({mr_url})"
        else:
            mr_link = "N/A"

        # Lark card message format
        card_content = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"{icon} AI Code Review Completed"
                },
                "template": color
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**Project:**\n{project_name}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**Author:**\n{user_name}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**MR:**\n{mr_link}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**Result:**\n{result_text}"
                            }
                        },
                    ]
                },
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": False,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**Branch:**\n`{source_branch}` → `{target_branch}`"
                            }
                        }
                    ]
                }
            ]
        }

        # Add additional content if provided
        if content:
            card_content["elements"].append({
                "tag": "hr"
            })
            card_content["elements"].append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": content
                }
            })

        # Add action button if MR URL is available
        if mr_url:
            card_content["elements"].append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "View Merge Request"
                        },
                        "type": "primary",
                        "url": mr_url
                    }
                ]
            })

        payload = {
            "msg_type": "interactive",
            "card": card_content
        }

        print(f"[INFO] Sending Lark notification to {webhook}")
        print(f"[DEBUG] Payload: {payload}")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(webhook, json=payload)

                if response.status_code == 200:
                    response_data = response.json()
                    if response_data.get("code") == 0:
                        print('[SUCCESS] Lark notification sent')
                        print(f'[DEBUG] Response: {response.text}')
                        return True
                    else:
                        print(
                            f'[ERROR] Lark notification failed: {response_data.get("msg")}')
                        print(f'[DEBUG] Response body: {response.text}')
                        return False
                else:
                    print(
                        f'[ERROR] Lark notification failed: {response.status_code}')
                    print(f'[DEBUG] Response body: {response.text}')
                    return False

        except Exception as e:
            print(f'[ERROR] Failed to send Lark notification: {str(e)}')
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
        Send error notification to Lark

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
            mr_link = f"[{mr_title}]({mr_url})"
        elif mr_url:
            mr_link = f"[View MR]({mr_url})"
        else:
            mr_link = mr_title

        # Lark card message format for errors
        card_content = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "❌ AI Code Review Failed"
                },
                "template": "red"
            },
            "elements": [
                {
                    "tag": "div",
                    "fields": [
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**Project:**\n{project_name}"
                            }
                        },
                        {
                            "is_short": True,
                            "text": {
                                "tag": "lark_md",
                                "content": f"**MR:**\n{mr_link}"
                            }
                        }
                    ]
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**Error:**\n{error_message}"
                    }
                }
            ]
        }

        # Add action button if MR URL is available
        if mr_url:
            card_content["elements"].append({
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {
                            "tag": "plain_text",
                            "content": "View Merge Request"
                        },
                        "type": "danger",
                        "url": mr_url
                    }
                ]
            })

        payload = {
            "msg_type": "interactive",
            "card": card_content
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(webhook, json=payload)

                if response.status_code == 200:
                    response_data = response.json()
                    return response_data.get("code") == 0

                return False

        except Exception as e:
            print(f'[ERROR] Failed to send Lark error notification: {str(e)}')
            return False
