import pathlib, datetime
from agent_core.stage import Stage

class Report(Stage):
    name = "report"
    def run(self, ctx):
        print(f"[{self.name}] sends reports")
        return ctx
