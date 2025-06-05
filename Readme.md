# BugFix Agent 🛠️🤖
_Small-LLM, multi-stage bot that **finds, patches & PRs bugs** in your repository using github actions—just by adding one workflow file._

---

## Features

| Feature | Description |
|---------|-------------|
| **Drop-in** | Copy a GitHub Actions workflow → the agent starts running in CI. |
| **Tool-augmented** | Fault localisation, patch synthesis, test-run validation inside **one** container. |
| **Cost-aware** | Uses smaller models by default with optional larger model fallback and cost controls. |
| **Secure** | All operations run within your CI environment with proper permission handling. |

---

## Quick start

1. **Add a workflow** to your repo at `.github/workflows/auto-fix.yml`:
   - Copy the workflow file from this repository's `.github/workflows/auto-fix.yml`
   - Copy the filter script from `.github/scripts/filter_issues.py`

2. **Configure required secrets** in your repository:
   - Go to Settings > Secrets and variables > Actions
   - Add `GOOGLE_API_KEY` or other LLM provider API key

3. **Enable PR creation permissions**:
   - Go to Settings > Actions > General
   - Scroll to "Workflow permissions"
   - Enable "Allow GitHub Actions to create and approve pull requests"
   - Click "Save"

4. **Customize behavior** (optional):
   - Create a `bugfix.yml` in your repository root
   - Override default settings (labels, max attempts, etc.)

## How It Works

The BugFix Agent operates in sequential stages:

1. **Prepare**: Sets up the environment and creates a new branch
2. **Localize**: Identifies the source of the bug in your codebase
3. **Fix**: Generates patches using LLM-based code synthesis
4. **Validate**: Builds and tests the proposed fixes
5. **Apply**: Commits changes to the branch
6. **Report**: Creates a pull request with the fix

Each issue with the configured label will be processed automatically, with multiple fix attempts if needed.



## local development
- [ ] TODO complete this section 
- .env for envrioment variables 
- docker-compose for local development

