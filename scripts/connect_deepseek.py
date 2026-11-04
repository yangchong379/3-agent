"""Local masked-key entry for the independent enterprise knowledge project."""
import argparse
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import sys
import warnings

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from knowledge_agent.cli import main


def read_secret(prompt):
    if sys.platform != "win32":
        return getpass.getpass(prompt)
    try:
        import tkinter as tk
        from tkinter import simpledialog
    except ImportError:
        raise RuntimeError("Windows password dialog requires tkinter") from None
    root = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        value = simpledialog.askstring(
            "DeepSeek API Key", "在这里粘贴新 API Key，然后点 OK。\n输入以星号显示，不会保存到文件。",
            show="*", parent=root)
        return value or ""
    except tk.TclError:
        raise RuntimeError("Cannot open password dialog") from None
    finally:
        if root is not None:
            root.destroy()


def next_destination(prefix):
    base = ROOT / "examples/runs"
    candidate = base / prefix
    number = 1
    while candidate.exists():
        number += 1
        candidate = base / f"{prefix}-{number}"
    return candidate


def retry_plan():
    summaries = []
    for path in (ROOT / "examples/runs").glob("live*/summary.json"):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("mode") == "live_model":
            summaries.append((value.get("generated_at_utc", ""), value))
    if not summaries:
        raise ValueError("没有已完成的真实评估，请先运行 --evaluate。")
    latest = max(summaries, key=lambda item: item[0])[1]
    return [c["case"] for c in latest["cases"] if not c["passed"]]


def connect(full=False, retry=False, secret_reader=None, runner=None, evaluator=None):
    selected = None
    if retry:
        try:
            selected = retry_plan()
        except (ValueError, OSError, KeyError):
            print("请先完成一次真实评估并保留summary.json，再重跑失败项。")
            return 4
        if not selected:
            print("最新真实评估没有失败项，无需调用模型。")
            return 0
    print("将进行多次真实模型API调用，按提供商规则计费。" if full or retry else "将运行真实模型的知识问答案例，会产生API费用。")
    print("请在本机密码窗口粘贴密钥，点OK；密钥不写入文件，也不要发送到聊天里。", flush=True)
    reader = secret_reader or read_secret
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            secret = reader("请输入API Key（隐藏输入）: ").strip()
    except (EOFError, KeyboardInterrupt, RuntimeError, getpass.GetPassWarning):
        print("未读取到密钥，请在自己的PowerShell窗口重试。")
        return 4
    if not secret or set(secret) == {"*"} or any(not 33 <= ord(c) <= 126 for c in secret):
        print("请输入实际密钥，不要输入星号、提示符或命令。")
        return 4
    settings = {"MODEL_API_KEY": secret, "MODEL_BASE_URL": "https://api.deepseek.com",
                "MODEL_NAME": "deepseek-flash", "MODEL_THINKING": "disabled"}
    previous = {name: os.environ.get(name) for name in settings}
    try:
        os.environ.update(settings)
        if full or retry:
            if evaluator is None:
                from evaluate import evaluate
                evaluator = evaluate
            destination = next_destination("live-retry" if retry else "live")
            print("运行记录目录：" + str(destination), flush=True)
            return evaluator("live", str(destination), case_names=selected)
        return (runner or main)(["--model", "live", "--input", str(ROOT / "examples/inputs/normal.json"),
            "--data", str(ROOT / "data/documents.json"),
            "--output", str(ROOT / "examples/runs/live-answer.json")])
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--evaluate", action="store_true")
    group.add_argument("--retry-failed", action="store_true")
    args = parser.parse_args()
    if sys.platform != "win32" and not sys.stdin.isatty():
        parser.exit(4, "请在交互式终端中运行并本机输入密钥。\n")
    raise SystemExit(connect(full=args.evaluate, retry=args.retry_failed))
