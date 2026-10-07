import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from .client import post_request
from .config import config_home, load_candidates, load_settings
from .launcher import collect_antigravity, launch_antigravity
from .routing import build_request, fixed_result, validate_result


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="依 models.json 為 codex、claude、antigravity 推薦模型；Antigravity 可在確認後於 Orca 開啟。"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    recommend = commands.add_parser("recommend", help="取得模型建議")
    recommend.add_argument("--client", required=True, help="models.json 中的 client 名稱")
    recommend.add_argument("--route", help="固定使用此分級（例如 Plan Mode 的 deep），不呼叫 Jev、不讀金鑰")
    collect = commands.add_parser("collect", help="取得狀態；使用者確認關閉後才關終端機")
    collect.add_argument("--job-dir", required=True, type=Path)
    collect.add_argument("--json", action="store_true")
    collect.add_argument("--close", action="store_true", help="關閉本次已完成的终端機")
    collect.add_argument("--confirmed", action="store_true", help="使用者已明確說關閉")
    launch = commands.add_parser("launch", help="使用者確認後，在 Orca 開啟 Antigravity 互動介面")
    launch.add_argument("--client", choices=["antigravity"], default="antigravity")
    launch.add_argument("--model", required=True, help="已選定的模型，必須在該 client 清單中")
    launch.add_argument("--confirmed", action="store_true", help="使用者已明確確認送出")
    launch.add_argument("--mode", choices=["default", "plan"], default="default")
    for command in (recommend, launch):
        question_args = command.add_mutually_exclusive_group(required=True)
        question_args.add_argument("--question", help="問題文字；填 - 則從 stdin 讀取")
        question_args.add_argument("--question-file", type=Path, help="UTF-8 問題檔案")
        context_args = command.add_mutually_exclusive_group()
        context_args.add_argument("--context", default="", help="必要的對話背景")
        context_args.add_argument("--context-file", type=Path, help="UTF-8 背景檔案")
        command.add_argument("--config-dir", type=Path, default=config_home())
        command.add_argument("--json", action="store_true", help="輸出 JSON，方便其他工具讀取")
        command.add_argument("--dry-run", action="store_true", help="只檢查請求或啟動設定，不讀金鑰或呼叫模型")
    args = parser.parse_args(argv)
    if args.command == "collect":
        try:
            result = collect_antigravity(args.job_dir, close=args.close, confirmed=args.confirmed)
        except (OSError, ValueError, KeyError, RuntimeError):
            print(json.dumps({"status": "error", "message": "無法讀取本次工作。"}, ensure_ascii=False))
            return 1
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        elif result.get("terminal_closed"):
            print("已關閉")
        elif result["status"] == "interactive_started":
            print("Antigravity 互動程序已啟動，請在 Orca 查看。看完請說「關閉」。")
        elif result["status"] == "completed":
            print("完成，答案在 Orca。看完請說「關閉」。")
        else:
            print(result["status"])
        return 1 if result["status"] == "error" else 0
    try:
        if args.question_file:
            question = args.question_file.read_text(encoding="utf-8-sig")
        else:
            question = sys.stdin.read() if args.question == "-" else args.question
        context = args.context_file.read_text(encoding="utf-8-sig") if args.context_file else args.context
        if not question.strip() or len(question) > 20000 or len(context) > 40000:
            raise ValueError("Invalid input")
        candidates = load_candidates(args.config_dir, args.client)
        if args.command == "launch":
            result = launch_antigravity(
                args.model, question, context, candidates,
                confirmed=args.confirmed, dry_run=args.dry_run, mode=args.mode,
            )
        elif args.route:
            result = fixed_result(candidates, args.route)
            result.update(client=args.client)
        elif args.dry_run:
            result = {
                "status": "dry_run", "api_called": False, "selected_model_called": False,
                "client": args.client,
                "request": build_request(question, context, candidates, "jev-latest"),
            }
        else:
            settings = load_settings(args.config_dir)
            body = build_request(question, context, candidates, settings["TYPESAFE_MODEL"])
            started = time.perf_counter()
            response = post_request(body, settings["TYPESAFE_API_KEY"])
            result = validate_result(response, candidates)
            result.update(client=args.client, latency_ms=round((time.perf_counter() - started) * 1000))
    except (OSError, ValueError, TypeError, RuntimeError, subprocess.TimeoutExpired) as exc:
        message = str(exc) if isinstance(exc, RuntimeError) else "請檢查輸入、共用設定或 Jev 回傳格式。"
        if args.json:
            print(json.dumps({"status": "error", "message": message, "selected_model_called": False},
                             ensure_ascii=False))
        else:
            print(message, file=sys.stderr)
        return 1
    if args.json or args.dry_run:
        print(json.dumps(result, ensure_ascii=False))
    elif args.command == "launch":
        print(f"已在 Orca 啟動：{result['model']}。看完請說「關閉」，再用 collect --close --confirmed 關閉終端機。")
    elif result["source"] == "fixed":
        print(f"固定分級 {result['route']}：{result['recommended_model']}（未呼叫 Jev）")
    else:
        print(f"Jev 建議：{result['recommended_model']}")
        print(f"Jev 信心值：{result['confidence']:.0%}（不代表答對的機率）")
        if not result["auto_send"]:
            print("等待你確認送出；尚未切換或呼叫被建議的模型。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
