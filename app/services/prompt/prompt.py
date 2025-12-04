import os
from typing import List, Dict
from pathlib import Path


class PromptService:
    """Prompt service class"""

    def __init__(self):
        """Initialize and cache prompt content"""
        # Get project root directory
        current_dir = Path(__file__).resolve().parent
        project_root = current_dir.parent.parent
        prompt_path = project_root / 'prompt' / 'prompt-zh.txt'

        # Read and cache prompt file
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.cache_prompt = f.read()

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
