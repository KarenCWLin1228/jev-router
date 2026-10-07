# Claude Code execution

- If the current model is the selected model, handle the task directly.
- Otherwise dispatch one agent with the Agent tool (`model` parameter). Pass the question, context, and project constraints, and state that the model is already chosen and must not be re-routed. Do not start extra agents.
- If no model-selectable Agent tool exists, ask the user to switch with `/model` (not a shell command) and send again.
- Send follow-ups to the same agent with SendMessage. If that entry point is gone, say so; never answer with the main model instead.
