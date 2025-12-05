from pathlib import Path
from typing import List, Dict

import typer
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
import pyfiglet

app = typer.Typer(help="MR Agent CLI")
console = Console()
ENV_FILE = Path(".env")

# 多语言文本字典
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "en": {
        "platform_title": "Platform Selection",
        "platform_desc": "Select platforms to support (multi-select, use space to check, arrow keys to move, enter to confirm)",
        "platform_question": "Which code hosting platforms do you want MR Agent to support?",
        "platform_error": "At least one platform must be selected",
        "no_selection": "No platform selected, initialization cancelled.",

        "lang_title": "Language Selection",
        "lang_desc": "Select default code review comment language (affects AI output language only)",
        "lang_question": "Default comment language?",

        "gitlab_title": "GitLab Configuration",
        "gitlab_desc": "If you plan to integrate GitLab MR, configure the following information.\nIf you don't use GitLab, you can press Enter to skip.",
        "gitlab_url": "GitLab Base URL (e.g., https://gitlab.example.com)",
        "gitlab_token": "GitLab Default Token (with api permission, leave empty to skip)",

        "github_title": "GitHub Configuration",
        "github_desc": "If you plan to integrate GitHub PR, configure the following information.\nDefault uses official api.github.com.",
        "github_url": "GitHub Base URL",
        "github_token": "GitHub Default Token (with repo permission, leave empty to skip)",

        "llm_title": "LLM Configuration",
        "llm_desc": "Configure LLM inference interface.\nFor example, use OpenAI compatible interface.",
        "llm_url": "LLM Base URL (e.g., https://api.openai.com, leave empty to skip)",
        "llm_key": "LLM API Key (leave empty to skip)",
        "llm_model": "LLM Model Name (e.g., gpt-4.1-mini)",

        "step": "Step",
        "choose_platforms": "Choose platforms...",
        "choose_lang": "Choose default comment language...",
        "config_gitlab": "Configure GitLab...",
        "config_github": "Configure GitHub...",
        "config_llm": "Configure LLM...",

        "confirm_title": "Confirmation",
        "confirm_desc": "About to generate the following .env content:\n\n",
        "complete_title": "Completed",
        "complete_desc": ".env generated at",

        "chinese": "Chinese",
        "japanese": "Japanese",
        "english": "English",
    },
    "zh": {
        "platform_title": "平台选择",
        "platform_desc": "选择要支持的平台（多选，空格勾选，方向键移动，回车确认）",
        "platform_question": "你希望 MR Agent 支持哪些代码托管平台？",
        "platform_error": "至少选择一个平台",
        "no_selection": "未选择平台，初始化已取消。",

        "lang_title": "语言选择",
        "lang_desc": "选择默认代码审查评论语言（仅影响 AI 输出语言）",
        "lang_question": "默认评论语言？",

        "gitlab_title": "GitLab 配置",
        "gitlab_desc": "如果你打算集成 GitLab MR，请配置以下信息。\n如果不使用 GitLab，可以按回车跳过。",
        "gitlab_url": "GitLab Base URL（例如：https://gitlab.example.com）",
        "gitlab_token": "GitLab 默认 Token（需要 api 权限，留空跳过）",

        "github_title": "GitHub 配置",
        "github_desc": "如果你打算集成 GitHub PR，请配置以下信息。\n默认使用官方 api.github.com。",
        "github_url": "GitHub Base URL",
        "github_token": "GitHub 默认 Token（需要 repo 权限，留空跳过）",

        "llm_title": "LLM 配置",
        "llm_desc": "配置 LLM 推理接口。\n例如，使用 OpenAI 兼容接口。",
        "llm_url": "LLM Base URL（例如：https://api.openai.com，留空跳过）",
        "llm_key": "LLM API Key（留空跳过）",
        "llm_model": "LLM 模型名称（例如：gpt-4.1-mini）",

        "step": "步骤",
        "choose_platforms": "选择平台...",
        "choose_lang": "选择默认评论语言...",
        "config_gitlab": "配置 GitLab...",
        "config_github": "配置 GitHub...",
        "config_llm": "配置 LLM...",

        "confirm_title": "确认",
        "confirm_desc": "即将生成以下 .env 内容：\n\n",
        "complete_title": "完成",
        "complete_desc": ".env 已生成于",

        "chinese": "中文",
        "japanese": "日语",
        "english": "英语",
    },
    "ja": {
        "platform_title": "プラットフォーム選択",
        "platform_desc": "サポートするプラットフォームを選択（複数選択可、スペースでチェック、矢印キーで移動、Enterで確定）",
        "platform_question": "MR Agent でサポートするコードホスティングプラットフォームは？",
        "platform_error": "少なくとも1つのプラットフォームを選択してください",
        "no_selection": "プラットフォームが選択されていません。初期化をキャンセルしました。",

        "lang_title": "言語選択",
        "lang_desc": "デフォルトのコードレビューコメント言語を選択（AI出力言語にのみ影響）",
        "lang_question": "デフォルトのコメント言語は？",

        "gitlab_title": "GitLab 設定",
        "gitlab_desc": "GitLab MR を統合する場合は、以下の情報を設定してください。\nGitLab を使用しない場合は、Enter キーでスキップできます。",
        "gitlab_url": "GitLab Base URL（例：https://gitlab.example.com）",
        "gitlab_token": "GitLab デフォルトトークン（api 権限が必要、空白でスキップ）",

        "github_title": "GitHub 設定",
        "github_desc": "GitHub PR を統合する場合は、以下の情報を設定してください。\nデフォルトは公式の api.github.com を使用します。",
        "github_url": "GitHub Base URL",
        "github_token": "GitHub デフォルトトークン（repo 権限が必要、空白でスキップ）",

        "llm_title": "LLM 設定",
        "llm_desc": "LLM 推論インターフェースを設定します。\n例えば、OpenAI 互換インターフェースを使用します。",
        "llm_url": "LLM Base URL（例：https://api.openai.com、空白でスキップ）",
        "llm_key": "LLM API Key（空白でスキップ）",
        "llm_model": "LLM モデル名（例：gpt-4.1-mini）",

        "step": "ステップ",
        "choose_platforms": "プラットフォームを選択...",
        "choose_lang": "デフォルトのコメント言語を選択...",
        "config_gitlab": "GitLab を設定...",
        "config_github": "GitHub を設定...",
        "config_llm": "LLM を設定...",

        "confirm_title": "確認",
        "confirm_desc": "以下の .env 内容を生成します：\n\n",
        "complete_title": "完了",
        "complete_desc": ".env が生成されました：",

        "chinese": "中国語",
        "japanese": "日本語",
        "english": "英語",
    }
}


def t(key: str, lang: str = "en") -> str:
    """Get translated text"""
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)


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
        default="",
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
            f"[bold cyan]{t('step', cli_lang)} 4[/bold cyan] {t('config_github', cli_lang)}")
        github_base, github_token = ask_github(cli_lang)

    console.print()
    console.print(
        f"[bold cyan]{t('step', cli_lang)} 5[/bold cyan] {t('config_llm', cli_lang)}")
    llm_base, llm_key, llm_model = ask_llm(cli_lang)

    # Generate .env content
    lines: list[str] = []
    lines.append(f"REPO_TARGETS={targets}")
    lines.append(f"REPO_REVIEW_LANG={review_lang}")

    if gitlab_base:
        lines.append(f"GITLAB_BASE_URL={gitlab_base}")
    if gitlab_token:
        lines.append(f"GITLAB_DEFAULT_TOKEN={gitlab_token}")

    if github_base:
        lines.append(f"GITHUB_BASE_URL={github_base}")
    if github_token:
        lines.append(f"GITHUB_DEFAULT_TOKEN={github_token}")

    if llm_base:
        lines.append(f"LLM_BASE_URL={llm_base}")
    if llm_key:
        lines.append(f"LLM_API_KEY={llm_key}")
    if llm_model:
        lines.append(f"LLM_MODEL={llm_model}")

    console.print()
    console.print(Panel(
        t("confirm_desc", cli_lang) + "\n".join(lines),
        title=t("confirm_title", cli_lang),
        border_style="magenta",
    ))

    # Uncomment to actually write file
    # content = "\n".join(lines) + "\n"
    # ENV_FILE.write_text(content, encoding="utf-8")

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
