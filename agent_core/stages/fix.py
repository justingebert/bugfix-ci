import os
import pathlib
from agent_core.stage import Stage
from google import genai
from google.genai import types


class Fix(Stage):
    name = "fix"
    def run(self, ctx):
        print(ctx.get("source_files"))
        file_path = pathlib.Path(ctx.get("source_files")[0])
        if not file_path:
            raise RuntimeError(f"[{self.name}] no source files found in context")

        original_code = file_path.read_text()

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
        fixed_code = response.text

        print(f" [{self.name}] LLM response: {fixed_code}")

        file_path.write_text(fixed_code)
        print(f"[{self.name}] wrote fixed code back to {file_path}")

        ctx["fixed_files"] = [str(file_path)]
        return ctx
