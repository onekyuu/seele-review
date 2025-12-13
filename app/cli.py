from pathlib import Path
from typing import List

import typer
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
import pyfiglet

from app.utils.i18n import t, get_available_languages

app = typer.Typer(help="MR Agent CLI")
console = Console()
ENV_FILE = Path(".env")


def print_banner_rainbow() -> None:
    """Oh My Zsh style rainbow gradient effect"""
    title_lines = [
        "  ███████╗███████╗███████╗██╗     ███████╗",
        "  ██╔════╝██╔════╝██╔════╝██║     ██╔════╝",
        "  ███████╗█████╗  █████╗  ██║     █████╗  ",
        "  ╚════██║██╔══╝  ██╔══╝  ██║     ██╔══╝  ",
        "  ███████║███████╗███████╗███████╗███████╗",
        "  ╚══════╝╚══════╝╚══════╝╚══════╝╚══════╝",
    ]

    rainbow_colors = [
        "bold red", "bold yellow", "bold green",
        "bold cyan", "bold blue", "bold magenta",
    ]

    console.print()
    for i, line in enumerate(title_lines):
        styled_text = Text(line, style=rainbow_colors[i % len(rainbow_colors)])
        console.print(Align.center(styled_text))

    console.print()

    subtitle = Text()
    subtitle.append("  ✨ ", style="bold yellow")
    subtitle.append("AI-Powered Code Review", style="bold white")
    subtitle.append(" ✨", style="bold yellow")
    console.print(Align.center(subtitle))

    tagline = Text("GitHub 🔀 GitLab 🔀 Powered by AI 🤖", style="italic cyan")
    console.print(Align.center(tagline))
    console.print()


def print_banner_ultimate() -> None:
    """Ultimate version: combining pyfiglet + rainbow colors"""
    try:
        ascii_art = pyfiglet.figlet_format("SEELE REVIEW", font="slant")
        lines = ascii_art.strip().split('\n')
        rainbow_colors = ["red", "yellow", "green", "cyan", "blue", "magenta"]

        console.print()
        for i, line in enumerate(lines):
            color = rainbow_colors[i % len(rainbow_colors)]
            console.print(Align.center(Text(line, style=f"bold {color}")))

        console.print()

        subtitle = Panel(
            "[bold white]🤖 AI-Powered Code Review for GitHub & GitLab 🚀[/bold white]\n"
            "[italic cyan]Let's make code review intelligent![/italic cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
        console.print(Align.center(subtitle))
        console.print()

    except ImportError:
        print_banner_rainbow()


def choose_cli_language() -> str:
    """Choose CLI interface language"""
    console.print(Panel(
        "Select CLI interface language / 选择界面语言 / インターフェース言語を選択",
        title="Language / 语言 / 言語",
        border_style="green",
    ))

    choice = questionary.select(
        "CLI interface language?",
        choices=[
            questionary.Choice("1) English", value="en"),
            questionary.Choice("2) 中文", value="zh"),
            questionary.Choice("3) 日本語", value="ja"),
        ],
        default="en",
    ).ask()

    if not choice:
        console.print(
            "[red]No language selected, initialization cancelled.[/red]")
        raise typer.Abort()

    return choice


def choose_targets(lang: str) -> str:
    """Choose platforms with i18n support"""
    console.print(Panel(
        t("platform_desc", lang),
        title=t("platform_title", lang),
        border_style="cyan",
    ))

    choices = [
        questionary.Choice("GitLab", value="gitlab", checked=True),
        questionary.Choice("GitHub", value="github", checked=False),
    ]

    selected: List[str] = questionary.checkbox(
        t("platform_question", lang),
        choices=choices,
        validate=lambda xs: True if xs else t("platform_error", lang),
    ).ask()

    if not selected:
        console.print(f"[red]{t('no_selection', lang)}[/red]")
        raise typer.Abort()

    return ",".join(selected)


def choose_lang(lang: str) -> str:
    """Choose review language with i18n support"""
    console.print(Panel(
        t("lang_desc", lang),
        title=t("lang_title", lang),
        border_style="green",
    ))

    choice = questionary.select(
        t("lang_question", lang),
        choices=[
            questionary.Choice(f"1) {t('chinese', lang)}", value="zh"),
            questionary.Choice(f"2) {t('japanese', lang)}", value="ja"),
            questionary.Choice(f"3) {t('english', lang)}", value="en"),
        ],
        default="zh",
    ).ask()

    if not choice:
        console.print(f"[red]{t('no_selection', lang)}[/red]")
        raise typer.Abort()

    return choice


def ask_gitlab(lang: str) -> tuple[str | None, str | None]:
    """Ask GitLab configuration with i18n support"""
    console.print(Panel(
        t("gitlab_desc", lang),
        title=t("gitlab_title", lang),
        border_style="yellow",
    ))

    gitlab_base = questionary.text(
        t("gitlab_url", lang),
        default="https://gitlab.com/api/v4",
    ).ask()

    gitlab_token = questionary.password(
        t("gitlab_token", lang),
        default="",
    ).ask()

    return gitlab_base or None, gitlab_token or None


def ask_github(lang: str) -> tuple[str | None, str | None]:
    """Ask GitHub configuration with i18n support"""
    console.print(Panel(
        t("github_desc", lang),
        title=t("github_title", lang),
        border_style="yellow",
    ))

    github_base = questionary.text(
        t("github_url", lang),
        default="https://api.github.com",
    ).ask()

    github_token = questionary.password(
        t("github_token", lang),
        default="",
    ).ask()

    return github_base or None, github_token or None


def ask_llm(lang: str) -> tuple[str | None, str | None, str | None]:
    """Ask LLM configuration with i18n support"""
    console.print(Panel(
        t("llm_desc", lang),
        title=t("llm_title", lang),
        border_style="blue",
    ))

    llm_base = questionary.text(
        t("llm_url", lang),
        default="",
    ).ask()

    llm_key = questionary.password(
        t("llm_key", lang),
        default="",
    ).ask()

    llm_model = questionary.text(
        t("llm_model", lang),
        default="gpt-4.1-mini",
    ).ask()

    return llm_base or None, llm_key or None, llm_model or None


def ask_notification(lang: str) -> tuple[str, str]:
    """Ask notification configuration with i18n support"""
    console.print(Panel(
        t('notification_desc', lang),
        title=t('notification_title', lang),
        border_style="magenta",
    ))

    # Use translated none text as key
    none_text = t('notification_none', lang)

    notification_service = questionary.select(
        t('notification_question', lang),
        choices=[
            none_text,
            "Slack",
            "Lark (飞书)",
        ],
        default=none_text,
    ).ask()

    # Get webhook URL if a service is selected
    notification_webhook = ""
    if notification_service != none_text:
        webhook_prompt = t('notification_webhook_prompt', lang).format(
            service=notification_service)
        notification_webhook = questionary.text(
            webhook_prompt,
            default="",
        ).ask()

    # Map to configuration values
    notification_type_map = {
        none_text: "none",
        "Slack": "slack",
        "Lark (飞书)": "lark",
    }

    notification_type = notification_type_map.get(notification_service, "none")

    return notification_type, notification_webhook or ""


@app.command()
def init():
    """Interactive .env initialization with i18n support"""
    print_banner_ultimate()

    # Step 0: Choose CLI language
    cli_lang = choose_cli_language()

    console.print(
        f"[bold cyan]{t('step', cli_lang)} 1[/bold cyan] {t('choose_platforms', cli_lang)}")
    targets = choose_targets(cli_lang)

    console.print()
    console.print(
        f"[bold cyan]{t('step', cli_lang)} 2[/bold cyan] {t('choose_lang', cli_lang)}")
    review_lang = choose_lang(cli_lang)

    gitlab_base = None
    gitlab_token = None
    github_base = None
    github_token = None

    targets_set = {t.strip() for t in targets.split(",")}

    if "gitlab" in targets_set:
        console.print()
        console.print(
            f"[bold cyan]{t('step', cli_lang)} 3[/bold cyan] {t('config_gitlab', cli_lang)}")
        gitlab_base, gitlab_token = ask_gitlab(cli_lang)

    if "github" in targets_set:
        console.print()
        console.print(
            f"[bold cyan]{t('step', cli_lang)} 3[/bold cyan] {t('config_github', cli_lang)}")
        github_base, github_token = ask_github(cli_lang)

    console.print()
    console.print(
        f"[bold cyan]{t('step', cli_lang)} 4[/bold cyan] {t('config_llm', cli_lang)}")
    llm_base, llm_key, llm_model = ask_llm(cli_lang)

    console.print()
    console.print(
        f"[bold cyan]{t('step', cli_lang)} 5[/bold cyan] {t('config_notification', cli_lang)}")
    notification_type, notification_webhook = ask_notification(cli_lang)

    # Generate .env content
    lines: list[str] = []
    lines.append(f"REPO_TARGETS={targets}")
    lines.append(f"REPO_REVIEW_LANG={review_lang}")

    if gitlab_base:
        lines.append(f"GITLAB_API_BASE={gitlab_base}")
    if gitlab_token:
        lines.append(f"GITLAB_TOKEN={gitlab_token}")

    if github_base:
        lines.append(f"GITHUB_API_BASE={github_base}")
    if github_token:
        lines.append(f"GITHUB_TOKEN={github_token}")

    if llm_base:
        lines.append(f"LLM_BASE_URL={llm_base}")
    if llm_key:
        lines.append(f"OPENAI_API_KEY={llm_key}")
    if llm_model:
        lines.append(f"AI_MODEL={llm_model}")

    # Notification Configuration
    lines.append(f"NOTIFICATION_PLATFORM={notification_type}")
    lines.append(f"NOTIFICATION_WEBHOOK_URL={notification_webhook}")

    # Legacy webhook URLs (deprecated, use NOTIFICATION_WEBHOOK_URL instead)
    lines.append(
        f"SLACK_WEBHOOK_AI_REVIEW={notification_webhook if notification_type == 'slack' else ''}")
    lines.append(
        f"LARK_WEBHOOK_URL={notification_webhook if notification_type == 'lark' else ''}")

    console.print()
    console.print(Panel(
        t("confirm_desc", cli_lang) + "\n".join(lines),
        title=t("confirm_title", cli_lang),
        border_style="magenta",
    ))

    # Uncomment to actually write file
    content = "\n".join(lines) + "\n"
    ENV_FILE.write_text(content, encoding="utf-8")

    console.print(Panel(
        f"{t('complete_desc', cli_lang)} {ENV_FILE.absolute()}",
        title=t("complete_title", cli_lang),
        border_style="green",
    ))


@app.command()
def run(
    host: str = typer.Option("0.0.0.0", help="Listen address"),
    port: int = typer.Option(8000, help="Port"),
    reload: bool = typer.Option(True, help="Enable auto-reload"),
):
    """Start FastAPI service"""
    import uvicorn

    console.print(Panel(
        f"Starting MR Agent service: {host}:{port}\nPress Ctrl+C to stop.",
        title="Running",
        border_style="cyan",
    ))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
    )


def main():
    app()


if __name__ == "__main__":
    main()
