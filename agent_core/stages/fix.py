import pathlib, datetime
from agent_core.stage import Stage

class Fix(Stage):
    name = "fix"
    def run(self, ctx):
        print(ctx)
        marker = pathlib.Path(ctx["workspace"])/"AGENT_WAS_HERE.txt"
        marker.write_text(f"hello at {datetime.datetime.now()}\n")
        print(f"[{self.name}] created {marker.relative_to(ctx['workspace'])}")
        return ctx
