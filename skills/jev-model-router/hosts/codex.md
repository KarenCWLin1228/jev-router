# Codex execution

- If you can confirm the current model is the selected model, handle the task directly. If you cannot confirm it, do not claim a switch.
- If a model-selectable agent dispatch tool exists, dispatch one agent. Pass the question, context, and project constraints, and state that the model is already chosen and must not be re-routed. Do not start extra agents.
- Otherwise say the model has not been switched and ask the user to switch and send again.
- Send follow-ups to the same agent. If that entry point is gone, say so; never answer with the main model instead.
