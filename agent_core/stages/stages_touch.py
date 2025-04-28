import pathlib, datetime
from agent_core.stage import Stage

class Touch(Stage):
    name = "touch"
    def run(self, ctx):
        marker = pathlib.Path(ctx["workspace"])/"AGENT_WAS_HERE.txt"
        marker.write_text(f"hello at {datetime.datetime.utcnow()}\n")
        print(f"[{self.name}] created {marker.relative_to(ctx['workspace'])}")
        return ctx
