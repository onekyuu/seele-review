import os
from typing import Optional, List, Dict, Any
from openai import AsyncOpenAI
from app.schemas.agent.review import QWenChatResponse
from app.services.agent.utils import extract_first_yaml_from_markdown
from app.services.prompt.prompt import PromptService


class AgentService:
    """Agent service class"""

    def __init__(self, prompt_service: PromptService):
        self.prompt_service = prompt_service
        self.api_key = os.getenv('QWEN_API_KEY', '')
        self.base_url = os.getenv(
            'LLM_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        self.ai_model = os.getenv('AI_MODEL', 'qwen3-max')

        # Initialize OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    async def get_prediction(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Get prediction result"""
        answer = await self.call_agent(query)
        print(f"=== Agent Answer:\n{answer}")
        result = extract_first_yaml_from_markdown(answer)
        print(f"=== Parsed Result:\n{result}")

        if result and result.error:
            raise result.error

        return result.parsed.get('reviews') if result and result.parsed else None

    async def call_agent(self, query: str) -> str:
        """Call Qwen API"""
        try:
            completion = await self.client.chat.completions.create(
                model=self.ai_model,
                messages=self.prompt_service.get_messages(query),
                temperature=0.2,
                max_tokens=6000,
                stream=True,
            )

            answer = ''

            async for chunk in completion:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        answer += delta.content

            return answer

        except Exception as e:
            print(f"Call Qwen API error: {e}")
            print(
                "Please refer to documentation: https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
            raise
