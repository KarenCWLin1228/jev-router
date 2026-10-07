# jev-model-router

On explicit invocation, Jev recommends a model. If you name `codex`, `claude`, or `antigravity`, that agent is locked and Jev only picks its model; otherwise the target depends on whether the question is everyday or software work. Jev confidence >= 80% runs immediately; below that it waits for you to reply "送出" (send). Plan Mode always uses deep without calling Jev and sends immediately.

This README is for people; it is not loaded into the model's context.

## Files

```text
jev-model-router/
  SKILL.md              core rules, loaded on invocation
  hosts/claude.md       read before dispatch when target is claude
  hosts/codex.md        read before dispatch when target is codex
  hosts/antigravity.md  read before dispatch when target is antigravity
  agents/openai.yaml    Codex: disable implicit invocation
  README.md             setup (this file)
```

## Prerequisites

1. Install [uv](https://docs.astral.sh/uv/).
2. Install the `jev-router` CLI and make sure `jev-router --help` runs in a terminal (uv's tool directory must be on PATH):

   ```shell
   uv tool install git+https://github.com/KarenCWLin1228/jev-router
   ```

3. Create the config directory `~/.config/jev/`:
   - `.env`: `TYPESAFE_API_KEY`, `TYPESAFE_MODEL`. Never commit or share it.
   - `models.json`: each client (`claude`, `codex`, `antigravity`) has `fast`, `standard`, and `deep` tiers. `description` tells Jev what each tier is for; change `model` to models your account can actually use. Example (the author's current settings):

     ```json
     {
       "codex": {
         "fast": {
           "model": "gpt-6-luna",
           "description": "Straightforward explanations and small deterministic changes with a known location and approach: text edits, simple configuration changes, or localized fixes. No substantial investigation or design choices are needed."
         },
         "standard": {
           "model": "gpt-6.1-sol",
           "description": "Routine feature implementation with clear requirements and existing patterns or examples. Normal coding and tests that require implementation work but little architectural uncertainty."
         },
         "deep": {
           "model": "gpt-6-astra",
           "description": "Unknown root causes, repeated failed fixes, cross-module architectural decisions, comparison of competing approaches, or complex reasoning with substantial uncertainty."
         }
       },
       "claude": {
         "fast": {
           "model": "sonnet",
           "description": "Straightforward explanations and small deterministic changes with a known location and approach: text edits, simple configuration changes, or localized fixes. No substantial investigation or design choices are needed."
         },
         "standard": {
           "model": "opus",
           "description": "Routine feature implementation with clear requirements and existing patterns or examples. Normal coding and tests that require implementation work but little architectural uncertainty."
         },
         "deep": {
           "model": "fable",
           "description": "Unknown root causes, repeated failed fixes, cross-module architectural decisions, comparison of competing approaches, or complex reasoning with substantial uncertainty."
         }
       },
       "antigravity": {
         "fast": {
           "model": "gemini-3.8-flash-low",
           "description": "Simple everyday explanations, direct facts, basic translations, and short messages."
         },
         "standard": {
           "model": "gemini-3.8-flash-medium",
           "description": "Routine everyday planning, travel itineraries, product comparisons, and writing with clear requirements and a modest number of constraints."
         },
         "deep": {
           "model": "gemini-3.1-pro-high",
           "description": "Everyday decisions requiring complex reasoning, many interacting constraints, comparison of difficult tradeoffs, or substantial uncertainty."
         }
       }
     }
     ```

4. The Antigravity target needs Windows, Orca, and the Antigravity CLI (`agy`). A named agent also needs a usable entry point in the current host; if it cannot run, the skill says so instead of switching agents.

## Install the skill

Copy the whole `jev-model-router` folder (in the repo under `skills/`) into your client's skills directory, for example `~/.claude/skills/` for Claude Code.

## Usage

```text
/jev-model-router [codex|claude|antigravity] <question>   (Claude Code)
$jev-model-router [codex|claude|antigravity] <question>   (Codex)
```

The leading agent is optional. With it, the agent is locked; without it, the target is chosen by purpose.

Example: `$jev-model-router use codex to plan a trip to Tainan` locks codex's model list; it does not switch to Antigravity just because the question is about travel.

- Jev confidence >= 0.80 sends the message to the agent immediately.
- Recommendations and execution reports start with "Jev pick: agent / model. Confidence: VALUE%." When Jev was not called, the report shows the actual source and "Confidence: n/a" instead of a made-up number.
- Antigravity shows its answer in the interactive UI; the main session never reads the full text. The terminal closes only after you say "關閉" (close); auto-send never closes it.
