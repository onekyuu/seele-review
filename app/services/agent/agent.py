import os
from typing import Optional, List
from openai import AsyncOpenAI
from app.schemas.agent.review import Review
from app.services.agent.utils import extract_first_yaml_from_markdown
from app.services.prompt.prompt import PromptService
from app.config import settings
from app.utils.token import TokenHandler, ChunkResult


class AgentService:
    """Agent service class with token management"""

    def __init__(self, prompt_service: PromptService):
        self.prompt_service = prompt_service
        self.api_key = settings.openai_api_key
        self.base_url = settings.llm_base_api
        self.ai_model = settings.ai_model

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        self.token_handler = TokenHandler(
            model=self.ai_model,
            max_tokens=6000,
            chunk_overlap=200
        )

    async def get_prediction(self, query: str) -> Optional[List[Review]]:
        """
        Get AI code review predictions with automatic chunking

        Args:
            query: Diff content to review

        Returns:
            List of Review objects or None
        """
        # Step 1: Check token count
        token_count = self.token_handler.count_tokens(query)
        print(f"[INFO] Query content: {token_count} tokens")

        # Step 2: Process single request if within limit
        if self.token_handler.is_within_limit(query):
            print("[INFO] Processing in single request")
            return await self._process_single_chunk(query)

        # Step 3: Split into chunks and process
        print(
            f"[WARNING] Content exceeds limit ({token_count} tokens), splitting...")
        chunks = self.token_handler.split_diff_by_files(query)
        print(f"[INFO] Split into {len(chunks)} chunks")

        # Step 4: Process each chunk
        chunk_results: List[ChunkResult] = []

        for i, chunk in enumerate(chunks):
            chunk_tokens = self.token_handler.count_tokens(chunk)
            print(
                f"[INFO] Processing chunk {i+1}/{len(chunks)} ({chunk_tokens} tokens)")

            try:
                reviews = await self._process_single_chunk(chunk)

                # Convert Review objects to dicts for merging
                reviews_dict = [review.model_dump() if reviews else {}
                                for review in (reviews or [])]

                chunk_results.append(ChunkResult(
                    chunk_index=i,
                    content=chunk,
                    token_count=chunk_tokens,
                    result={"reviews": reviews_dict}
                ))

            except Exception as e:
                print(f"[ERROR] Failed to process chunk {i+1}: {e}")
                chunk_results.append(ChunkResult(
                    chunk_index=i,
                    content=chunk,
                    token_count=chunk_tokens,
                    result=None
                ))

        # Step 5: Merge and deduplicate results
        merged_reviews_dict = self.token_handler.merge_reviews(chunk_results)
        print(
            f"[SUCCESS] Merged {len(merged_reviews_dict)} unique reviews from {len(chunks)} chunks")

        # Convert back to Review objects
        if merged_reviews_dict:
            return [Review(**review_dict) for review_dict in merged_reviews_dict]

        return None

    async def _process_single_chunk(self, query: str) -> Optional[List[Review]]:
        """
        Process single chunk of content

        Args:
            query: Diff content chunk

        Returns:
            List of Review objects or None
        """
        answer = await self.call_agent(query)
        result = extract_first_yaml_from_markdown(answer)

        if result and result.error:
            print(f"[ERROR] YAML parse error: {result.error}")
            raise result.error

        if result and result.parsed:
            reviews_data = result.parsed.get('reviews', [])
            if reviews_data:
                return [Review(**review_dict) for review_dict in reviews_data]

        return None

    async def call_agent(self, query: str) -> str:
        """
        Call AI API with streaming

        Args:
            query: Query content

        Returns:
            AI response text
        """
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
            print(f"[ERROR] Call AI API error: {e}")
            print("Please refer to documentation: https://help.aliyun.com/zh/model-studio/developer-reference/error-code")
            raise
