import tiktoken
from app.config import settings
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class ChunkResult:
    """Single chunk processing result"""
    chunk_index: int
    content: str
    token_count: int
    result: Any


class TokenHandler:
    """Manage token counting, splitting, and merging for LLM context"""

    def __init__(
        self,
        model: str = settings.ai_model,
        max_tokens: int = 8000,
        chunk_overlap: int = 200
    ):
        try:
            self.encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            self.encoding = tiktoken.get_encoding("cl100k_base")

        self.max_tokens = max_tokens
        self.chunk_overlap = chunk_overlap

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))

    def is_within_limit(self, text: str, max_tokens: Optional[int] = None) -> bool:
        """Check if text is within token limit"""
        limit = max_tokens or self.max_tokens
        return self.count_tokens(text) <= limit

    def split_by_tokens(
        self,
        text: str,
        max_tokens: Optional[int] = None
    ) -> List[str]:
        """Split text by token count (fallback method)"""
        limit = max_tokens or self.max_tokens
        tokens = self.encoding.encode(text)

        if len(tokens) <= limit:
            return [text]

        chunks = []
        start = 0

        while start < len(tokens):
            end = min(start + limit, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)
            chunks.append(chunk_text)

            if end < len(tokens):
                start = end - self.chunk_overlap
            else:
                break

        return chunks

    def split_diff_by_files(
        self,
        diff_content: str,
        max_tokens: Optional[int] = None
    ) -> List[str]:
        """
        Smart split diff content by files

        Diff format (from prompt):
        ```
        ## new_path: test.js
        ## old_path: test.js
        @@ -5,3 +5,9 @@ console.log("test.js 4")
        (5, 5)   console.log("test.js 5")
        ( , 8)  +console.log("test.js 8")
        ```

        Args:
            diff_content: Complete diff content with custom format
            max_tokens: Maximum tokens per chunk

        Returns:
            List of diff chunks
        """
        limit = max_tokens or self.max_tokens

        # Split by file markers (## new_path: and ## old_path:)
        files = []
        current_file_lines = []
        in_file = False

        lines = diff_content.split('\n')
        i = 0

        # Preserve header (commit message, etc.) before first file
        header_lines = []
        while i < len(lines):
            line = lines[i]
            if line.startswith('## new_path:') or line.startswith('## old_path:'):
                break
            header_lines.append(line)
            i += 1

        header = '\n'.join(header_lines).strip()

        # Process file diffs
        while i < len(lines):
            line = lines[i]

            # Detect file header start (## new_path: ...)
            if line.startswith('## new_path:'):
                # Save previous file
                if current_file_lines:
                    file_content = '\n'.join(current_file_lines)
                    files.append(file_content)

                # Start new file
                current_file_lines = [line]
                in_file = True

            # Continue current file
            elif in_file:
                current_file_lines.append(line)

                # Check if next line is a new file marker
                if i + 1 < len(lines) and lines[i + 1].startswith('## new_path:'):
                    # Current file ends here
                    file_content = '\n'.join(current_file_lines)
                    files.append(file_content)
                    current_file_lines = []
                    in_file = False

            i += 1

        # Add last file
        if current_file_lines:
            file_content = '\n'.join(current_file_lines)
            files.append(file_content)

        print(f"[DEBUG] Split into {len(files)} files")

        # Group files into chunks that fit token limit
        chunks = []
        current_chunk = []
        current_tokens = 0

        # Add header to first chunk
        if header:
            header_tokens = self.count_tokens(header)
            current_chunk.append(header)
            current_tokens = header_tokens

        for file_diff in files:
            file_tokens = self.count_tokens(file_diff)

            # If single file exceeds limit, split it by tokens
            if file_tokens > limit:
                # Save current chunk
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split large file
                print(
                    f"[WARNING] Single file exceeds limit ({file_tokens} tokens), splitting...")
                file_chunks = self.split_by_tokens(file_diff, limit)
                chunks.extend(file_chunks)

            # Try to add file to current chunk
            elif current_tokens + file_tokens + 2 <= limit:  # +2 for '\n\n' separator
                current_chunk.append(file_diff)
                current_tokens += file_tokens + 2

            # Start new chunk
            else:
                if current_chunk:
                    chunks.append('\n\n'.join(current_chunk))
                current_chunk = [file_diff]
                current_tokens = file_tokens

        # Add remaining chunk
        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        print(f"[DEBUG] Created {len(chunks)} chunks")
        for i, chunk in enumerate(chunks):
            tokens = self.count_tokens(chunk)
            print(f"[DEBUG] Chunk {i+1}: {tokens} tokens")

        return chunks

    def merge_reviews(
        self,
        chunk_results: List[ChunkResult]
    ) -> List[Dict[str, Any]]:
        """
        Merge review results from multiple chunks

        Expected AI response format (YAML from prompt):
        ```yaml
        reviews:
          - newPath: src/agent/agent.service.ts
            oldPath: src/agent/agent.service.ts
            startLine: 1
            endLine: 1
            type: old
            issueHeader: 逻辑错误
            issueContent: ...
        ```

        Args:
            chunk_results: List of chunk processing results

        Returns:
            Merged and deduplicated review items
        """
        all_reviews = []

        for chunk_result in chunk_results:
            if not chunk_result.result:
                continue

            result = chunk_result.result

            # Handle different response formats
            if isinstance(result, dict):
                # Case 1: Response has 'reviews' key (standard format)
                if 'reviews' in result:
                    reviews = result['reviews']
                    if isinstance(reviews, list):
                        all_reviews.extend(reviews)
                    else:
                        all_reviews.append(reviews)
                else:
                    # Case 2: Single review object
                    all_reviews.append(result)

            elif isinstance(result, list):
                # Case 3: Already a list of reviews
                all_reviews.extend(result)

            else:
                # Unknown format
                all_reviews.append(result)

        print(f"[DEBUG] Total reviews before dedup: {len(all_reviews)}")

        # Deduplicate by (newPath/oldPath, startLine, endLine, type)
        unique_reviews = {}

        for review in all_reviews:
            if not isinstance(review, dict):
                continue

            # Extract fields (support both camelCase from YAML and snake_case)
            new_path = (
                review.get('newPath') or
                review.get('new_path') or
                review.get('file_path', '')
            )
            old_path = (
                review.get('oldPath') or
                review.get('old_path') or
                new_path
            )
            start_line = (
                review.get('startLine') or
                review.get('start_line') or
                review.get('line_number', 0)
            )
            end_line = (
                review.get('endLine') or
                review.get('end_line') or
                start_line
            )
            review_type = review.get('type', 'new')

            # Create unique key based on location
            key = (new_path, start_line, end_line, review_type)

            # Keep first occurrence or merge issues
            if key not in unique_reviews:
                unique_reviews[key] = review
            else:
                # Merge issue content from same location
                existing = unique_reviews[key]

                # Get issue content fields (support multiple field names)
                existing_content = (
                    existing.get('issueContent') or
                    existing.get('issue_content') or
                    existing.get('comment', '')
                )
                new_content = (
                    review.get('issueContent') or
                    review.get('issue_content') or
                    review.get('comment', '')
                )

                if new_content and new_content not in existing_content:
                    # Merge with separator
                    merged_content = f"{existing_content}\n---\n{new_content}".strip()

                    # Update with proper field name
                    if 'issueContent' in existing:
                        existing['issueContent'] = merged_content
                    elif 'issue_content' in existing:
                        existing['issue_content'] = merged_content
                    else:
                        existing['comment'] = merged_content

                    print(
                        f"[DEBUG] Merged duplicate review at {new_path}:{start_line}-{end_line}")

        final_reviews = list(unique_reviews.values())
        print(f"[DEBUG] Final reviews after dedup: {len(final_reviews)}")

        return final_reviews
