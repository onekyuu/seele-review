import os
from typing import List, Dict
from pathlib import Path
from app.config import settings


class PromptService:
    """Prompt service class"""

    def __init__(self):
        """Initialize and cache prompt content"""
        # Get project root directory
        current_dir = Path(__file__).resolve().parent
        # app/services/prompt -> app/services -> app -> project_root/app
        app_dir = current_dir.parent.parent

        lang = str(settings.repo_review_lang).lower(
        ) if settings.repo_review_lang else 'en'

        filename = f'prompt-{lang}.txt'
        prompt_path = app_dir / 'prompt' / filename

        if not prompt_path.exists():
            print(
                f"[WARNING] Prompt file {filename} not found, falling back to English.")
            prompt_path = app_dir / 'prompt' / 'prompt-en.txt'

        try:
            with open(prompt_path, 'r', encoding='utf-8') as f:
                self.cache_prompt = f.read()
        except Exception as e:
            print(f"[ERROR] Failed to load prompt: {e}")
            self.cache_prompt = "You are a code review expert."

    def get_messages(self, query: str) -> List[Dict[str, str]]:
        """Get message list"""
        return [
            {
                'role': 'system',
                'content': self.cache_prompt,
            },
            {
                'role': 'user',
                'content': query,
            },
        ]
