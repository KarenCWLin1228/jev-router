# jev-router

A small command-line tool that asks **Jev** (a routing model served by the [TypeSafe](https://docs.typesafe.ai/patterns/intent-routing) API) which model tier a task needs, then returns a recommendation that a coding agent such as Claude Code or Codex can act on.

It also ships the **`jev-model-router` skill** (in [`skills/jev-model-router/`](skills/jev-model-router/)), which wires the CLI into Claude Code and Codex.

```text
            your question (+ optional context)
                          |
                          v
   jev-router recommend --client <codex|claude|antigravity>
                          |
             +------------+-------------+
             |                          |
        --route deep               Jev via TypeSafe API
     (fixed tier, no API)     (picks fast / standard / deep)
             |                          |
             +------------+-------------+
                          v
     JSON: recommended_model, confidence, auto_send, ...
                          |
       +------------------+-------------------+
       |                                      |
  codex / claude                          antigravity
  host agent dispatches               jev-router launch -> Orca terminal
  the chosen model                    jev-router collect [--close]
```

`jev-router` **only recommends**. It never calls the recommended model itself. The one exception is `launch`, which starts the Antigravity CLI in an Orca terminal, and only when you pass `--confirmed`.

## Contents

- [Requirements](#requirements)
- [Install](#install)
- [Configure](#configure)
- [Commands](#commands)
  - [recommend](#recommend)
  - [launch (Antigravity)](#launch-antigravity)
  - [collect (Antigravity)](#collect-antigravity)
- [Output reference](#output-reference)
- [Using it from Claude Code and Codex](#using-it-from-claude-code-and-codex)
- [Privacy and security](#privacy-and-security)
- [Limitations](#limitations)
- [Development](#development)
- [License](#license)

## Requirements

| Need | For | Notes |
|---|---|---|
| Python 3.12+ | everything | uv can install it for you |
| [uv](https://docs.astral.sh/uv/) | installing the CLI | `uv tool install` puts `jev-router` on your PATH |
| TypeSafe API key | `recommend` (without `--route`) | Not needed for `--dry-run` or `--route` |
| Windows, Orca, Antigravity CLI (`agy`) | `launch` / `collect` only | `agy` is expected at `~/AppData/Local/agy/bin/agy.exe`; `orca` must be on PATH |

## Install

Install the CLI straight from GitHub:

```shell
uv tool install git+https://github.com/KarenCWLin1228/jev-router
jev-router --help
```

If `jev-router` is not found, run `uv tool update-shell` and open a new terminal.

To upgrade later:

```shell
uv tool upgrade jev-router
```

### Windows install script (optional)

Cloning the repo and running `install-local.ps1` installs the CLI **and** creates the config folder in one step:

```powershell
git clone https://github.com/KarenCWLin1228/jev-router
cd jev-router
.\install-local.ps1
```

The script:

1. Runs `uv tool install --reinstall` on the cloned folder.
2. Creates `~/.config/jev/` (or `$env:JEV_ROUTER_CONFIG_DIR`) and restricts it to your Windows account.
3. If `.env` does not exist yet, writes it with `TYPESAFE_API_KEY` taken from the environment variable of the same name or, if unset, from a hidden prompt. `TYPESAFE_MODEL` defaults to `jev-latest`.
4. If `models.json` does not exist yet, copies `models.example.json`.

It never overwrites an existing `.env` or `models.json` and never prints the key.

### Install the skill

Copy `skills/jev-model-router/` into your agent's skills folder, for example `~/.claude/skills/jev-model-router/` for Claude Code. See the [skill README](skills/jev-model-router/README.md) for usage.

## Configure

All settings live in one folder, `~/.config/jev/` by default:

```text
~/.config/jev/
  .env          TypeSafe credentials (secret)
  models.json   candidate models per client and tier
```

Override the folder with `--config-dir <path>` or the `JEV_ROUTER_CONFIG_DIR` environment variable.

### `.env`

```dotenv
TYPESAFE_API_KEY=your-key-here
TYPESAFE_MODEL=jev-latest
```

- Only these two keys are read. Everything else in the file is ignored.
- Single-line values, optional quotes, and a trailing ` # comment` on unquoted values are supported. Variables are not expanded and nothing is executed.
- Environment variables with the same names take precedence over the file.
- `TYPESAFE_MODEL` defaults to `jev-latest` when omitted.

### `models.json`

Each client has its own tiers. Every tier needs a `model` (the identifier the client accepts) and a `description` (what Jev reads to decide which tier fits).

```json
{
  "claude": {
    "fast":     { "model": "sonnet", "description": "Straightforward explanations and small deterministic changes ..." },
    "standard": { "model": "opus",   "description": "Routine feature implementation with clear requirements ..." },
    "deep":     { "model": "fable",  "description": "Unknown root causes, repeated failed fixes, architectural decisions ..." }
  }
}
```

[`models.example.json`](models.example.json) is the author's full setup for `codex`, `claude`, and `antigravity`. **Change the model names to ones your account can actually use**; jev-router does not check account access, and custom gateways may use different names. Tier names are free-form, but the skill's Plan Mode expects a `deep` tier.

## Commands

### recommend

Ask Jev which tier fits a question.

```shell
jev-router recommend --client claude --question "Why does this test fail only on CI?" --json
```

| Option | Meaning |
|---|---|
| `--client NAME` | Required. A client key from `models.json` (`codex`, `claude`, `antigravity`, ...). |
| `--question TEXT` / `--question-file PATH` | Required, one of them. `--question -` reads stdin. Max 20,000 characters. |
| `--context TEXT` / `--context-file PATH` | Optional background, max 40,000 characters. Use it so a short follow-up like "why?" is not mistaken for an easy question. |
| `--route TIER` | Skip Jev and return that tier's model (for example `deep` in Plan Mode). Needs no API key. |
| `--dry-run` | Print the request Jev would receive. Reads no key and makes no network call. |
| `--json` | Print JSON for other tools. |
| `--config-dir PATH` | Use another config folder. |

Files are read as UTF-8 (a BOM is fine). Prefer `--question-file` for long or multi-line text to avoid shell quoting problems. Inputs are never truncated; oversized input is an error.

Examples:

```shell
# Short follow-up with the context Jev needs
jev-router recommend --client codex --question "Why?" --context "Same fix attempted three times; still failing." --json

# Long question from files
jev-router recommend --client claude --question-file question.txt --context-file context.txt --json

# Fixed tier, no API call (used by the skill in Plan Mode)
jev-router recommend --client claude --route deep --question-file question.txt --json

# Inspect the request without a key or network
jev-router recommend --client claude --question "Explain the user field" --dry-run
```

Without `--json`, the command prints a short human-readable summary (currently in Traditional Chinese).

### launch (Antigravity)

Open the Antigravity CLI with the chosen model in a dedicated Orca terminal. This is the only command that starts a model, so it refuses to run without `--confirmed`.

```shell
jev-router launch --client antigravity --model gemini-3.8-flash-low --question-file question.txt --confirmed --json
```

| Option | Meaning |
|---|---|
| `--model MODEL` | Required. Must appear in the `antigravity` list in `models.json`. |
| `--confirmed` | Required unless `--dry-run`. Means the user approved sending. |
| `--mode plan` | Start Antigravity in plan mode. |
| `--dry-run` | Check that `agy` and `orca` exist and the model is configured; start nothing. |
| question / context / `--json` / `--config-dir` | Same as `recommend`. |

What happens:

1. Checks that `agy models` lists the requested model. If not, it stops; it never substitutes another model.
2. Writes the request to a private temp folder (`jev-antigravity-*`) so your text never appears on a command line.
3. Creates an Orca terminal titled **"Jev · Antigravity"** in the active worktree and starts `agy --model <MODEL> --prompt-interactive=<prompt>` there, with `~/.local/share/jev-router/antigravity` as the working directory. Tool permissions are not bypassed.
4. Asks Orca to focus that tab. If that fails, `focus_requested` is `false`; open the tab yourself. The terminal is still running.

The session stays interactive: you read the answer and ask follow-ups directly in Antigravity. jev-router never reads the answer.

### collect (Antigravity)

Check a launched job, and close its terminal when you are done.

```shell
jev-router collect --job-dir JOB_DIR --json
jev-router collect --job-dir JOB_DIR --close --confirmed --json
```

| Status | Meaning |
|---|---|
| `pending` | The worker has not reported yet. Collect again; do not relaunch. |
| `interactive_started` | Antigravity is running. It does **not** mean the answer is finished. |
| `exited` | You left the Antigravity CLI normally. |
| `error` | Antigravity failed to start or exited abnormally. Nothing is retried. |
| `closed` | `--close --confirmed` closed the terminal and deleted the job folder. |

- A plain `collect` never closes anything or deletes files.
- `--close` requires `--confirmed`, and only closes the terminal this job created.
- If closing fails, `terminal_closed` stays `false` and the job folder is kept.
- `answer_verified` and `answer_displayed` are always `false`: the tool deliberately does not look at the answer.

## Output reference

`recommend --json` on success:

```json
{
  "recommended_model": "sonnet",
  "route": "fast",
  "probabilities": { "fast": 0.94, "standard": 0.06, "deep": 0.0 },
  "confidence": 0.91,
  "jev_model": "jev-1.13.0",
  "source": "jev",
  "auto_send": true,
  "status": "awaiting_send",
  "selected_model_called": false,
  "client": "claude",
  "latency_ms": 358
}
```

| Field | Meaning |
|---|---|
| `recommended_model` | The `model` value of the chosen tier. |
| `route` | The chosen tier name. |
| `probabilities` | Jev's distribution over tiers (Jev results only). |
| `confidence` | Jev's own confidence, or `null` for `--route`. It is **not** the probability that the answer will be correct. |
| `jev_model` | The Jev version that answered (Jev results only). |
| `source` | `jev` or `fixed` (`--route`). |
| `auto_send` | `true` when the raw confidence is at least 0.80 (not rounded, so 0.7999 is `false`), and always `true` for `--route`. Agents may dispatch without asking when this is `true`. |
| `status` | Always `awaiting_send` on success. |
| `selected_model_called` | Always `false`; jev-router never runs the recommended model. |
| `latency_ms` | Round-trip time of the Jev call. |

On failure the exit code is `1` and, with `--json`, the output is `{"status": "error", "message": "...", "selected_model_called": false}`. jev-router never fabricates a recommendation, never retries, and never falls back to another model. Jev results are validated: the choice must be a configured tier, the probabilities must cover exactly the configured tiers and sum to 1, and the chosen tier must be the most likely one.

## Using it from Claude Code and Codex

The CLI cannot change the model your agent is running; the agent does that. The bundled skill handles it:

1. You run `/jev-model-router [codex|claude|antigravity] <question>` (Claude Code) or `$jev-model-router ...` (Codex).
2. The skill picks the target agent: the one you named, otherwise Antigravity for everyday questions and the current host for software work.
3. It calls `jev-router recommend` (with `--route deep` in Plan Mode).
4. If `auto_send` is `true` it dispatches immediately; otherwise it waits for you to reply "送出" (send).
5. Claude Code dispatches a sub-agent with the chosen model, Codex uses its agent dispatch, and Antigravity goes through `launch` / `collect`.

Without the skill, you can do the same by hand: run `recommend --json`, then switch with `/model <model>` in Claude Code or start a new session with `claude --model <model>`.

## Privacy and security

- **What leaves your machine:** `recommend` sends your question and context to `https://api.typesafe.ai/v1/systemone`. Do not include secrets in them. `--dry-run` and `--route` send nothing.
- **The API key** is only sent in the `Authorization` header to that fixed HTTPS endpoint. It is never printed, logged, or included in error messages, and provider error bodies are not echoed.
- **No history:** jev-router keeps no cache or log of questions. Antigravity job folders are temporary handoff files, deleted on `--close --confirmed`. Antigravity keeps its own conversation history.
- **No shell injection:** your text is passed through files and argument lists, never interpolated into a shell command.
- **Never commit `~/.config/jev/.env`.** This repo's `.gitignore` excludes `.env` files.

## Limitations

- `launch` / `collect` are Windows-only and require Orca. `recommend` works anywhere Python runs.
- The Antigravity worker prompt currently asks for answers in Traditional Chinese, and CLI messages are in Traditional Chinese.
- jev-router cannot start Codex or Claude itself. Running Codex from Claude Code (or the reverse) is not supported.
- Model names in `models.json` are not checked against your account.
- One Jev call per run, 25-second timeout, no automatic retry.

## Development

All tests use mocks; nothing calls a paid API, Orca, or Antigravity. From the repo root:

```shell
uv run --isolated --no-project --with-editable . python -m unittest discover -s tests -v
uvx ruff check .
uv build
```

Use `--with-editable .` rather than `--with .`; the latter can reuse a cached build and test stale code.

Layout:

```text
src/jev_router/
  cli.py        argument parsing and output
  config.py     reads .env and models.json
  client.py     single HTTPS call to TypeSafe
  routing.py    builds the Jev request, validates the answer, auto_send, --route
  launcher.py   launch / collect for Antigravity via Orca
  worker.py     runs inside the Orca terminal and starts agy
tests/          offline unit tests
skills/jev-model-router/   the agent skill
```

## License

[MIT](LICENSE)
