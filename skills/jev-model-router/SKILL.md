---
name: jev-model-router
description: Pick a model with Jev for an optional agent (codex, claude, antigravity). Confidence >= 80% or Plan Mode runs immediately; otherwise wait for "送出".
argument-hint: "[codex|claude|antigravity] <question>"
disable-model-invocation: true
---

# Jev Model Router

Reply briefly in the user's language. Never fabricate results, retry, switch agents or models, read `.env`, or embed user text in shell commands.

## 1. Target

- Arguments starting with `codex`, `claude`, or `antigravity`, or an explicit "use X", lock that agent. Merely mentioning a product does not.
- Otherwise: everyday questions → `antigravity`; software work → current host. Ask if unclear.
- If the target cannot run here, say so.

## 2. Model

1. With the Write tool, write the question to `TMP/jev-q.txt` and the context to `TMP/jev-c.txt` (`TMP` = the absolute system temp folder). Context is only the task, prior failures, and constraints.
2. Run exactly this one command, with nothing chained before or after it:

```shell
jev-router recommend --client TARGET --question-file TMP/jev-q.txt --context-file TMP/jev-c.txt --json
```

- Do not pre-check the command, create folders, or delete files with the shell; the two files are overwritten next time.
- Host-declared Plan Mode: add `--route deep` (no Jev call). The run is plan-only.
- User names a model: skip the CLI; source is the user and it waits for "送出".
- Use the result only if exit code is `0` and `status` is `awaiting_send`; otherwise explain and stop. If the command is not found, point to this skill's `README.md`.

Show one line, then act:

- `source: jev` → "Jev pick: TARGET / MODEL. Confidence: VALUE%."
- otherwise → "Source: Plan Mode / user. TARGET / MODEL. Confidence: n/a."
- `auto_send: true` → execute this turn. Otherwise wait for "送出".

## 3. Execute

- Read `hosts/<target>.md` and follow it; if unreadable, stop.
- Before authorization (`auto_send` or "送出"), do not answer, edit, or call the model. Authorization covers dispatch only, not push, merge, or email.
- Start every report with the shown line, then the real status. Never present the current model's answer as the selected model's.

## State

- Keep the pending item (question, context, target, mode, model, source, confidence) in the conversation.
- "送出" runs it without calling Jev again. "好", "謝謝" are not a send.
- Edits while waiting re-route; a new question cancels it. Follow-ups keep the model; re-route only on request.
