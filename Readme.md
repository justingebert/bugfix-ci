# APR Core 🛠️
_A lightweight Automated Program Repair system that **finds, patches & PRs bugs** in your repository using GitHub Actions._

---

## Features

| Feature | Description |
|---------|-------------|
| **Drop-in** | Copy a GitHub Actions workflow → APR Core starts running in CI. |
| **Tool-augmented** | Fault localization, patch synthesis, test-run validation inside **one** container. |
| **Cost-aware** | Uses smaller models by default with optional larger model fallback and cost controls. |
| **Secure** | All operations run within your CI environment with proper permission handling. |

---

## Quick start

1. **Add a workflow**
   - Copy the workflow file from this repository `.github/workflows/auto-fix.yml`.
   - Copy the filter script from `.github/scripts/filter_issues.py`.

2. **Configure required secrets** in your repository:
   - Go to Settings > Secrets and variables > Actions
   - Add `LLM_API_KEY` as a repository secret

3. **Enable PR creation permissions**:
   - Go to Settings > Actions > General
   - Scroll to "Workflow permissions"
   - Enable "Allow GitHub Actions to create and approve pull requests"
   - Click "Save"

4. **Customize behavior** (optional):
   - Create a `bugfix.yml` in your repository root.
   - Override default settings like `label`, `model`, and `max_attempts`.

## How It Works

APR Core operates in sequential stages within a GitHub Actions workflow:

1. **Localize**: Identifies potential buggy files using information from the bug report (e.g., issue body, comments).
2. **Fix**: Generates patches using an LLM. It constructs a detailed prompt containing the source code of suspicious files and feedback from previous failed attempts.
3. **Build**: Verifies that the code builds successfully with the proposed fix. For Python projects, this may involve syntax checking or code formatting.
4. **Test**: Runs the project's test suite to validate the proposed fix.
5. **Apply**: If the fix is successful, the changes are committed to a new branch.
6. **Report**: A pull request is created with the fix, linking it to the original issue.

Each issue with the configured label will be processed automatically, with multiple fix attempts if needed. The system provides feedback between attempts to improve repair success rates.

## Local development
- Create a `.env` file for environment variables:
```dotenv
GITHUB_TOKEN=your_personal_access_token
GITHUB_REPOSITORY=owner/repo_name
LLM_API_KEY=your_llm_api_key
```
- Use the `run_local.sh` script to execute the repair process on your local machine. This requires Docker to be installed 
