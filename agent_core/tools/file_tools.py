import re
def clean_code_from_llm_response(response_text, original_code):
    """Clean markdown formatting from LLM response."""
    # First try to extract code from markdown code blocks
    code_block_pattern = r'```(?:python)?\s*(.*?)\s*```'
    code_blocks = re.findall(code_block_pattern, response_text, re.DOTALL)

    if code_blocks:
        return max(code_blocks, key=len)  # Return the longest code block

    # Remove markdown markers if present
    cleaned = re.sub(r'```(?:python)?\s*', '', response_text)
    cleaned = re.sub(r'```\s*', '', cleaned)

    # If the cleaned text looks valid, use it
    if cleaned.strip() and 'def ' in cleaned:
        return cleaned.strip()

    # As a last resort, use the original response
    return response_text.strip()