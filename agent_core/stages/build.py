import pathlib, datetime
from agent_core.stage import Stage

class Build(Stage):
    name = "build"
    def run(self, ctx):
        print(f"[{self.name}] runs build 👷")
        return ctx
