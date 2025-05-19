import os
import pathlib
import logging
from agent_core.stage import Stage
from google import genai
from google.genai import types

from agent_core.tools.file_tools import clean_code_from_llm_response


class Fix(Stage):
    name = "fix"
    def run(self, ctx):
        logging.info(ctx.get("source_files"))
        file_path = pathlib.Path(ctx.get("source_files")[0])
        if not file_path:
            raise RuntimeError(f"[{self.name}] no source files found in context")

        original_code = file_path.read_text()

        additional_context = ctx.get("previous_attempt_feedback", "")

        if additional_context:
            prompt = f"""
                        The following Python code has a bug. I tried to fix it before and attached some context. Please fix the Bug.

                        {original_code}

                        {additional_context}
                        """
        else:
            prompt = f"""
                        The following Python code has a bug. Please fix the Bug.

                        {original_code}
                        """

        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            config=types.GenerateContentConfig(
                system_instruction="You are part of an automated bug-fixing system. Please return the complete, corrected raw source file, never use any markdown formatting."),
            contents=prompt,
        )
        raw_response = response.text

        fixed_code = clean_code_from_llm_response(raw_response, original_code)

        logging.info(f" [{self.name}] LLM response: {fixed_code}")

        file_path.write_text(fixed_code)
        logging.info(f"[{self.name}] wrote fixed code back to {file_path}")

        ctx["fixed_files"] = [str(file_path)]
        return ctx
