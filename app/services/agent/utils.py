import re
from typing import Optional, List
import yaml
from app.schemas.agent.review import YamlContent, MRReview, Review


def fix_yaml_format_issues(yaml_content: str) -> str:
    """Fix YAML format issues"""
    lines = yaml_content.split('\n')
    fixed_lines: List[str] = []
    in_review_item = False

    for i, line in enumerate(lines):
        # Detect if it's a new review item
        if line.strip().startswith('- newPath:') or line.strip().startswith('-newPath:'):
            in_review_item = True
            # Ensure correct format
            line = '  - newPath: |'

        # Handle fields within review item
        elif in_review_item:
            trimmed_line = line.strip()

            # Check if it's a field name (contains colon)
            if ':' in trimmed_line:
                # Extract field name and value
                colon_index = trimmed_line.index(':')
                field_name = trimmed_line[:colon_index].strip()
                field_value = trimmed_line[colon_index + 1:].strip()

                # Handle common field names
                valid_fields = ['newPath', 'oldPath', 'startLine',
                                'endLine', 'type', 'issueHeader', 'issueContent']

                if field_name in valid_fields:
                    # For multi-line string fields, use | syntax
                    if field_name in ['newPath', 'oldPath', 'type', 'issueHeader', 'issueContent']:
                        line = f'    {field_name}: |'
                    else:
                        # For numeric fields, assign directly
                        line = f'    {field_name}: {field_value}'
                else:
                    # If field name is not in expected list, might be indentation issue
                    # Try to fix indentation
                    line = f'    {trimmed_line}'

            # Handle field values (non-field name lines)
            elif trimmed_line:
                # Ensure correct indentation (field values should have 2 more spaces than field names)
                line = f'      {trimmed_line}'

            # Check if next is another review item
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line.startswith('- newPath:') or next_line.startswith('-newPath:'):
                    in_review_item = False

        fixed_lines.append(line)

    return '\n'.join(fixed_lines)


def extract_first_yaml_from_markdown(markdown_text: str, is_parse: bool = True) -> Optional[YamlContent]:
    """Extract first YAML block from Markdown"""
    regex = r'```yaml\s*([\s\S]*?)\s*```'
    match = re.search(regex, markdown_text)

    if not match:
        return None

    yaml_content: str = match.group(1)
    result = YamlContent(
        content=yaml_content,
        fixedContent=None,
        parsed=None,
        error=None,
        fixApplied=False
    )

    if is_parse:
        try:
            # Try to parse directly first
            mr_review_dict = yaml.safe_load(yaml_content)

            if mr_review_dict and 'reviews' in mr_review_dict and isinstance(mr_review_dict['reviews'], list):
                # Clean possible newline characters
                for review in mr_review_dict['reviews']:
                    review['newPath'] = review.get(
                        'newPath', '').replace('\n', '')
                    review['oldPath'] = review.get(
                        'oldPath', '').replace('\n', '')
                    review['type'] = review.get(
                        'type', 'new').replace('\n', '')

                # Convert to Pydantic model
                mr_review = MRReview(**mr_review_dict)
                result.parsed = mr_review.model_dump()

        except yaml.YAMLError as yaml_error:
            # If direct parsing fails, try to fix format then parse
            print(
                f'Direct parsing failed: {yaml_error}, trying to fix format...')
            try:
                fixed_yaml_content = fix_yaml_format_issues(yaml_content)
                result.fixedContent = fixed_yaml_content
                result.fixApplied = True

                mr_review_dict = yaml.safe_load(fixed_yaml_content)

                if mr_review_dict and 'reviews' in mr_review_dict and isinstance(mr_review_dict['reviews'], list):
                    # Clean possible newline characters
                    for review in mr_review_dict['reviews']:
                        review['newPath'] = review.get(
                            'newPath', '').replace('\n', '')
                        review['oldPath'] = review.get(
                            'oldPath', '').replace('\n', '')
                        review['type'] = review.get(
                            'type', 'new').replace('\n', '')

                    # Convert to Pydantic model
                    mr_review = MRReview(**mr_review_dict)
                    result.parsed = mr_review.model_dump()

                print('Format fix successful, parsing completed')

            except Exception as fix_error:
                result.error = fix_error
                print(
                    f'Parsing still failed after format fix: {str(fix_error)}')
        except Exception as e:
            # Catch other exceptions (such as Pydantic validation errors)
            result.error = e
            print(f'Error occurred during parsing: {str(e)}')

    return result
