from agent_core.stage import Stage
class Logging(Stage):
    name = "logging"
    def run(self, ctx):
        msg = f"[{self.name}] running in {ctx['workspace']}"
        print(msg)
        ctx["logs"].append(msg)
        return ctx
