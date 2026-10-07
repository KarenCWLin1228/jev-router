import json
import subprocess
import sys
from pathlib import Path


def record_status(job, result):
    temporary = job / "result.tmp"
    temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    temporary.replace(job / "result.json")


def run_job(job):
    request = json.loads((job / "request.json").read_text(encoding="utf-8"))
    workspace = Path.home() / ".local/share/jev-router/antigravity"
    workspace.mkdir(parents=True, exist_ok=True)
    prompt = ("請用繁體中文回答。模型已選定，不要再呼叫 Jev。這是生活問題，"
              "不要讀取或修改開發專案。需要最新資訊時請查證；無法查證請明說。\n"
              + (f"必要背景：\n{request['context']}\n" if request["context"] else "")
              + request["question"])
    command = [request["executable"], "--model", request["model"], "--prompt-interactive=" + prompt]
    if request["mode"] == "plan":
        command.extend(["--mode", "plan"])
    result = dict(client="antigravity", model=request["model"], answer_verified=False,
                  answer_displayed=False)
    try:
        # 繼承 Orca 終端機的輸入與輸出，保留真正的互動介面。
        process = subprocess.Popen(command, cwd=workspace)
    except OSError:
        result.update(status="error", message="Antigravity 未成功啟動；不會重試或換模型。")
        record_status(job, result)
        return 1
    result.update(status="interactive_started", pid=process.pid, process_started=True)
    record_status(job, result)
    # 不讀畫面、紀錄或答案；程序存在不代表初始回答已完成。
    code = process.wait()
    result.update(status="exited" if code == 0 else "error", exit_code=code)
    if code:
        result["message"] = "Antigravity 已異常退出；不會重試或換模型。"
    record_status(job, result)
    return code


if __name__ == "__main__":
    raise SystemExit(run_job(Path(sys.argv[1])))
