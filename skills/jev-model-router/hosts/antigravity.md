# Antigravity execution

## Main session is already Antigravity

- Judge by the host-provided identity and full model name, never by the question text or whether `agy.exe` exists.
- Exact same model: answer directly, no CLI. Different or unverifiable: use the CLI below.
- Do not use native subagents: their model field only offers `inherit` / `flash` / `pro`, which are not verified full slugs, and the answer would flow back into the main session ([docs](https://antigravity.google/docs/subagents?tab=cli)).

## Launch

Add `--confirmed` only when authorized (`auto_send` or "送出"); otherwise only recommend or `--dry-run`. Use the model from the routing state:

```shell
jev-router launch --client antigravity --model 'MODEL' --question-file 'Q' --confirmed --json
```

- Add `--context-file` when there is context; add `--mode plan` while the host is in Plan Mode.
- The launcher checks `agy models` and opens a dedicated Orca terminal in interactive mode (`--prompt-interactive`). After answering it stays in Antigravity for direct follow-ups. jev-router picks the working directory; tool permissions are not bypassed.
- `focus_requested: false`: ask the user to open the "Jev · Antigravity" tab in Orca. Do not relaunch.

## Collect

`status: launched` only means started. Keep `job_dir` and `terminal_handle`:

```shell
jev-router collect --job-dir 'JOB_DIR' --json
```

- The answer stays in Orca and never enters the main session. Do not read the terminal or transcripts, or ask for the full text; do not summarize, repost, or fact-check it.
- `pending`: keep collecting; do not relaunch.
- `interactive_started`: reply "Antigravity is running; check Orca. Say '關閉' when done." Do not claim the answer is finished or displayed. Keep `job_dir`, `terminal_handle`, model, and confidence as the pending-close item.
- `exited`: the user left the interactive CLI; this does not mean done. Keep the terminal.
- `error`: say it failed. Do not fabricate, switch models, or retry. Do not infer completion from whether the shell exited.

## Close

- Run `collect --job-dir 'JOB_DIR' --close --confirmed --json` only when the user explicitly says "關閉" (close) and it maps to this item. Ask if it maps to none or several. Auto-send never authorizes closing.
- `terminal_closed: true`: reply "closed" and clear the pending-close item. On failure keep the state; do not call the model again.
- Follow-ups in the main session do not open a new CLI and never use `--continue`; a new task is routed again.
- Afterward delete this run's question and context temp files.
