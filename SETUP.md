# One-time setup

## 1. Create the repository

Create a new public, standalone GitHub repository named `ai-daily-briefs`. Use `main` as its default branch. Do not create it as a fork.

Upload this package or push it from Git, keeping the directory structure unchanged.

## 2. Add the Gemini API key

In the repository, open:

`Settings` -> `Secrets and variables` -> `Actions` -> `Secrets`

Create this repository secret:

| Name | Value |
| --- | --- |
| `GEMINI_API_KEY` | Your Gemini API key |

Never add the key to a source file, commit, issue or README.

The workflow uses `gemini-3.8-flash` by default. To change it without editing code, create an Actions variable named `GEMINI_MODEL` containing another supported model endpoint.

If the key is temporarily unavailable, the program can produce a conservative source-based fallback. The AI-generated mode is strongly recommended for the intended natural writing quality.

## 3. Contribution attribution

The workflow is already configured with the GitHub-associated no-reply address confirmed on the repository's first commit:

`100158505+iamvishno@users.noreply.github.com`

No attribution setup is required. If your GitHub username or account changes later, open:

`Settings` -> `Secrets and variables` -> `Actions` -> `Variables`

Create these variables:

| Name | Value |
| --- | --- |
| `GIT_AUTHOR_NAME` | `Vishnu Vardhan` |
| `GIT_AUTHOR_EMAIL` | The new exact GitHub-associated no-reply email |

GitHub will not attribute daily commits to your contribution graph if the email is not associated with your account.

## 4. Allow the workflow to write

Open:

`Settings` -> `Actions` -> `General` -> `Workflow permissions`

Choose `Read and write permissions`, then save.

## 5. Run the checks

Open the `Actions` tab and run `Quality checks`. It must pass before activation.

Then open `Daily AI brief` and select `Run workflow`. Confirm that it:

1. Creates one file under `daily/YYYY/MM/`.
2. Updates the latest-briefs section in `README.md`.
3. Creates one commit on `main`.
4. Does not create a second post when run again on the same day.

## 6. Verify the first contribution

Open the new commit and confirm that the author is linked to your GitHub account. GitHub may not update the contribution graph immediately.

## Local commands

Run all tests:

```bash
python -m unittest discover -s tests -v
```

Preview a post without writing files:

```bash
PYTHONPATH=src python scripts/run_daily.py --fixture tests/fixtures/sample_feed.xml --dry-run
```

Generate a local test entry from the fixture:

```bash
PYTHONPATH=src python scripts/run_daily.py --fixture tests/fixtures/sample_feed.xml
```
