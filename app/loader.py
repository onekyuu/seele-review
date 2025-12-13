"""Dynamic module loader based on configuration"""
from pathlib import Path
from typing import List, Optional
from fastapi import FastAPI
from app.config import settings
from rich.console import Console

console = Console()


class DynamicLoader:
    """Load modules dynamically based on configuration"""

    def __init__(self, app: FastAPI):
        self.app = app
        self.loaded_platforms: List[str] = []

    def load_all(self):
        """Load all configured modules"""
        self.load_platforms()
        self.load_notification()
        self.load_prompt()

    def load_platforms(self) -> List[str]:
        """Load platform routers based on REPO_TARGETS"""
        platforms = [p.strip().lower()
                     for p in str(settings.repo_targets).split(',') if p.strip()]

        for platform in platforms:
            if self._load_platform(platform):
                self.loaded_platforms.append(platform)

        return self.loaded_platforms

    def _load_platform(self, platform: str) -> bool:
        """Load a specific platform router"""
        try:
            if platform == 'gitlab':
                from app.routers.gitlab import router
                self.app.include_router(router)
                console.print(f"[green]✓[/green] Loaded GitLab router")
                return True

            elif platform == 'github':
                from app.routers.github import router
                self.app.include_router(router)
                console.print(f"[green]✓[/green] Loaded GitHub router")
                return True

            else:
                console.print(
                    f"[yellow]⚠[/yellow] Unknown platform: {platform}")
                return False

        except ImportError as e:
            console.print(f"[red]✗[/red] Failed to load {platform}: {e}")
            return False

    def load_notification(self) -> Optional[str]:
        """Load notification service based on NOTIFICATION_PLATFORM"""
        service = str(settings.notification_platform).lower()

        if service == 'none':
            console.print("[dim]○ No notification service configured[/dim]")
            return None

        try:
            if service == 'slack':
                from app.services.notification.slack import SlackNotifier
                console.print(f"[green]✓[/green] Loaded Slack notifier")

            elif service == 'lark':
                from app.services.notification.lark import LarkNotifier
                console.print(f"[green]✓[/green] Loaded Lark notifier")

            return service

        except ImportError as e:
            console.print(
                f"[red]✗[/red] Failed to load {service} notifier: {e}")
            return None

    def load_prompt(self) -> bool:
        """Verify prompt file based on REPO_REVIEW_LANG"""
        lang = str(settings.repo_review_lang).lower()
        prompt_path = Path(f"app/prompt/prompt-{lang}.txt")

        if prompt_path.exists():
            console.print(
                f"[green]✓[/green] Loaded prompt for language: [bold cyan]{lang}[/bold cyan]")
            return True
        else:
            console.print(
                f"[red]✗[/red] Prompt file not found: [bold]{prompt_path}[/bold]")
            console.print(
                f"[yellow]![/yellow] Defaulting to English or check your configuration")
            return False
