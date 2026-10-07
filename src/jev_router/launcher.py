import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def orca_call(executable, arguments):
    reply = subprocess.run([executable, *arguments, "--json"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=30)
    data = json.loads(reply.stdout) if not reply.returncode else {}
    if not data.get("ok"):
        raise RuntimeError("Orca 操作未成功；不會重複啟動。")
    return data["result"]


def launch_antigravity(model, question, context, candidates, confirmed=False, dry_run=False, mode="default"):
    if not dry_run and not confirmed:
        raise ValueError("Launch requires confirmation")
    if model not in {item["model"] for item in candidates.values()}:
        raise ValueError("Model is not configured")
    executable = Path.home() / "AppData/Local/agy/bin/agy.exe"
    orca = shutil.which("orca")
    if not executable.is_file() or not orca:
        raise RuntimeError("需要已安裝的 Antigravity CLI 和 Orca。")
    result = dict(status="launch_preview", client="antigravity", model=model, mode=mode,
                  target="orca", process_started=False, answer_verified=False)
    if dry_run:
        return result
    inventory = subprocess.run([str(executable), "models"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=30,
                               stdin=subprocess.DEVNULL)
    observed = {line.split()[0] for line in inventory.stdout.splitlines() if line.strip()}
    if inventory.returncode or model not in observed:
        raise RuntimeError("Antigravity 未提供指定模型；不會改用其他模型。")
    job = Path(tempfile.mkdtemp(prefix="jev-antigravity-"))
    request = dict(model=model, question=question, context=context, mode=mode,
                   executable=str(executable), orca=orca)
    (job / "request.json").write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")

    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    command = f"& {quote(sys.executable)} -m jev_router.worker {quote(job)}"
    terminal = orca_call(orca, ["terminal", "create", "--worktree", "active", "--title",
                               "Jev · Antigravity", "--shell", "powershell.exe",
                               "--command", command])["terminal"]["handle"]
    (job / "terminal.json").write_text(json.dumps({"handle": terminal}), encoding="utf-8")
    result.update(status="launched", process_started=True, job_dir=str(job), terminal_handle=terminal)
    # 建立成功後先記錄識別，再切換畫面；切換失敗不重建終端機。
    try:
        orca_call(orca, ["terminal", "switch", "--terminal", terminal])
        result["focus_requested"] = True
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        result["focus_requested"] = False
    return result


def collect_antigravity(job_dir, close=False, confirmed=False):
    if close and not confirmed:
        raise ValueError("Close requires confirmation")
    job = Path(job_dir).resolve()
    if job.parent != Path(tempfile.gettempdir()).resolve() or not job.name.startswith("jev-antigravity-"):
        raise ValueError("Invalid job directory")
    request = json.loads((job / "request.json").read_text(encoding="utf-8"))
    terminal = json.loads((job / "terminal.json").read_text(encoding="utf-8"))["handle"]
    if not close and not (job / "result.json").is_file():
        return dict(status="pending", terminal_handle=terminal, terminal_closed=False)
    result = (json.loads((job / "result.json").read_text(encoding="utf-8"))
              if (job / "result.json").is_file() else {"status": "pending"})
    # 舊工作也只回傳狀態，避免把答案帶進主對話。
    result = {key: result[key] for key in (
        "status", "client", "model", "conversation_id", "answer_verified", "answer_displayed", "message",
        "pid", "process_started", "exit_code"
    ) if key in result}
    result.update(terminal_handle=terminal, terminal_closed=False)
    if not close:
        return result
    try:
        closed = orca_call(request["orca"], ["terminal", "close", "--terminal", terminal])
        result["terminal_closed"] = closed["close"]["ptyKilled"] is True
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired):
        return result
    if result["terminal_closed"]:
        result["status"] = "closed"
        for name in ("request.json", "terminal.json", "result.json", "result.tmp"):
            (job / name).unlink(missing_ok=True)
        job.rmdir()
    return result
