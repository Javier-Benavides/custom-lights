# Threat model

This is a public repository where issues are worked by AI agents. Anyone on the internet can write text that an agent may read. This page says what could go wrong and what stops it.

**The main idea:** prompt injection has no complete defense. So assume an agent will be fooled one day, and make sure a fooled agent can do very little.

## What we protect

| Asset | Why it matters |
|---|---|
| The maintainer's machine and tokens | An agent with broad access is a remote control |
| Users' machines | `system/install.sh` runs as root |
| The board and the devices | A wrong chip command could write to flash, and a wrong device command could save over the owner's settings |
| Users' keystrokes | The keyboard's configuration interface also carries the keys being pressed |
| Users' location | The one private piece of data here |
| People watching the lights | Fast flashes can harm people with photosensitive epilepsy |
| The `main` branch and these instructions | Whoever changes them steers every future agent |

## Attacks and defenses

| # | Attack | Defense | Checked by |
|---|---|---|---|
| 1 | An issue or comment tells the agent what to do | Public text is data. Only a maintainer's spec is a task | Process, `AGENTS.md` |
| 2 | Hidden text: HTML comments, zero-width characters, image alt text | `tools/check_text.py --stdin` flags them before an agent reads | Tool |
| 3 | The author edits the issue after approval | The task lives in the maintainer's spec comment, not in the issue body | Process |
| 4 | A form auto-applies the label that starts an agent | Forms only apply `needs-triage`. `ai-ready` is set by hand | `tests/test_architecture.py` |
| 5 | A PR changes `AGENTS.md` or adds a `.claude/` folder to steer agents | Agents take instructions from `main`, never from a PR. Protected paths need the owner | CODEOWNERS |
| 6 | Instructions inside code comments, docs, test data or a linked page | The same rule: they are data. Links are not followed unless the spec lists them | Process |
| 7 | Script injection: an issue title lands in a shell step | Workflows use no event text in `run:` | `tests/test_architecture.py` |
| 8 | A fork PR steals secrets in CI | No `pull_request_target`, no secrets, read-only token | `tests/test_architecture.py` |
| 9 | A hijacked GitHub Action | Actions are pinned to a full commit, and Dependabot proposes updates | `tests/test_architecture.py` |
| 10 | A malicious dependency | There are no dependencies | `tests/test_architecture.py` |
| 11 | A PR adds a flash write to the chip, or a save to a device | Each allow-list is tested against the forbidden commands | `tests/hardware/`, `tests/test_architecture.py`, CODEOWNERS |
| 12 | A PR changes what runs as root | `system/` is protected, and scripts stay short enough to read | CODEOWNERS |
| 13 | Data is sent to a new host | Only `luces/data/fetch.py` runs `curl`, and hosts are on a list | `tests/test_architecture.py` |
| 14 | A real location is committed | `place.toml` is ignored by git. Forms warn about it | `tests/test_architecture.py`, `.gitignore` |
| 15 | A change makes the lights flash too fast | Tested on the light that leaves the service, and settings refuse fast values | `tests/scenes/test_sun.py`, `settings.py` |
| 16 | A data feed sends something strange | Strict parsers, 64 KB limit, HTTPS only. No model ever reads that data | `tests/data/` |
| 17 | Lookalike characters hide a change in a diff | Bidirectional and invisible characters fail the build | `tools/check_text.py` in CI |
| 18 | Pressure: "urgent", "the maintainer agreed", "security fix, merge now" | Claims in text grant nothing. Urgency is a reason to stop | Process |
| 19 | An agent's own honest mistake | Everything an agent writes is untrusted code until a person reviews it | Branch protection |
| 20 | A change reads or keeps the keys pressed on the keyboard | Key reports are only counted. The service has no network. Access to that interface is granted only when the keyboard is enabled | `tests/hardware/test_xpg_sorcerer.py`, `tests/test_devices.py`, CODEOWNERS |

## Limiting a fooled agent

These matter more than any filter:

- **No secrets.** An agent gets a short-lived token for one repository. Never a personal token, never an SSH key.
- **Isolation.** Run it in a container or a cloud sandbox, with no access to your home folder. Never on your daily machine with your own credentials.
- **No merge rights.** It pushes a branch and opens a draft PR. A person merges.
- **No workflow rights.** Its token cannot change `.github/`.
- **No network when it can be avoided.** The tests need none.
- **A human gate before and after.** Nothing starts without a maintainer's label, and nothing lands without a maintainer's review.

## What remains

- A maintainer can approve a bad spec or miss something in a review. Keep specs small and diffs short.
- New ways to hide text will appear. `tools/check_text.py` is a filter, not a guarantee.
- A chip command that is harmless on one board may not be on another.
- This model was written before the project had real contributors. Review it when that changes.

## Sources

- [Security model of claude-code-action](https://github.com/anthropics/claude-code-action/blob/main/docs/security.md)
- [PromptPwnd: AI agents in CI/CD tricked by issue text](https://www.csoonline.com/article/4101751/ai-in-ci-cd-pipelines-can-be-tricked-into-behaving-badly-2.html)
- [WCAG 2.2: three flashes or below threshold](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html)
