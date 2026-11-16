# Maintaining

Settings that live on GitHub, not in the code. The repository is only as safe as these.

## Before the first public push

- [ ] Check the author name and email of the commits: use GitHub's `noreply` address to keep your email private.
- [ ] Start from a fresh history, never from a private repository.
- [ ] Search the tree for your location, your name and your hostnames.
- [ ] Replace `@GITHUB_USER` in `.github/CODEOWNERS`.

## Repository settings

**Branch protection for `main`:**

- [ ] Require a pull request, with 1 approval.
- [ ] Require review from Code Owners.
- [ ] Dismiss stale approvals when new commits arrive.
- [ ] Require the `tests` check.
- [ ] Do not allow force pushes or deletions.

**Actions:**

- [ ] Workflow permissions: read repository contents only.
- [ ] Do not let Actions create or approve pull requests.
- [ ] Require approval to run workflows for all outside contributors.

**Security:**

- [ ] Enable private vulnerability reporting.
- [ ] Enable Dependabot alerts and secret scanning with push protection.

## Labels

Create the labels listed in [ai-workflow.md](ai-workflow.md): `needs-triage`, `bug`, `enhancement`, `physics`, `hardware`, `docs`, `ai-ready`, `needs-human`, `needs-eyes` and `security`.

## Triage

1. Read the raw issue, not just the rendered page: the pencil icon or the API shows hidden comments.
2. Run the text through the check:

   ```bash
   python3 tools/check_text.py --stdin < issue.md
   ```

3. Decide: close it, ask for more, mark `needs-human`, or write a spec.
4. If an AI drafts the spec, read every line: posting it is your approval.
5. Add `ai-ready`.

## Releases

Bump `__version__` in `luces/__init__.py` and `USER_AGENT` in `luces/data/fetch.py`, and tag the commit. There is no package to publish.
