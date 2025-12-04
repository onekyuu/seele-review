import os
from typing import Optional, List
from openai import AsyncOpenAI
from app.schemas.agent.review import Review
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

        # init OpenAI client
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    async def get_prediction(self, query: str) -> Optional[List[Review]]:
        """Get prediction result"""
        answer = await self.call_agent(query)
        result = extract_first_yaml_from_markdown(answer)

        if result and result.error:
            raise result.error

        if result and result.parsed:
            reviews_data = result.parsed.get('reviews', [])
            # Convert dict list to Review model list
            return [Review(**review_dict) for review_dict in reviews_data]

        return None

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
