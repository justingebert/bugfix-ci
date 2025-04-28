# BugFix Agent 🛠️🤖
_Small-LLM, multi-stage bot that **finds, patches & PRs bugs** in your repository—just by adding one workflow file._

---

## Features
| ✅ | Description |
|----|-------------|
| **Drop-in**        | Copy a 15-line GitHub Actions workflow → the agent starts running in CI. |
| **Tool-augmented** | Fault localisation, patch synthesis, test-run & security scan inside **one** container. |
| **Cost-aware**     | Uses GPT-3.5 / open-source models by default; optional GPT-4 fallback with cost cap. |

---

## Quick start

1. **Add a workflow** to your repo at `.github/workflows/auto-fix.yml`:

