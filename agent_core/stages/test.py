import pathlib, datetime
from agent_core.stage import Stage

class Touch(Stage):
    name = "touch"
    def run(self, ctx):
        print(f"[{self.name}] runs tests")
        return ctx
