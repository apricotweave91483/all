#!/usr/bin/env python3
import argparse
import json
import os
import smtplib
import sys
from dataclasses import dataclass
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Any

HTML_TEMPLATE = """<!doctype html>
<html>
  <body style=\"margin:0;padding:0;background:fafafa;font-family:'Courier New',monospace;\">
    <table role=\"presentation\" width=\"100%\" cellspacing=\"0\" cellpadding=\"0\" style=\"padding:36px 0;\">
      <tr><td align=\"center\">
        <table role=\"presentation\" width=\"560\" cellspacing=\"0\" cellpadding=\"0\" style=\"background:#111111;border-radius:0;border:2px dashed #22c55e;padding:34px;\">
          <tr><td style=\"color:#22c55e;font-size:13px;\">[ WEEKLY CSES ]</td></tr>
          <tr><td style=\"color:#dcfce7;font-size:30px;font-weight:700;padding-top:10px;\">{problem_name}</td></tr>
          <tr><td style=\"padding-top:24px;\"><a href=\"{problem_url}\" style=\"display:inline-block;background:#16a34a;color:#052e16;text-decoration:none;font-size:16px;font-weight:700;padding:10px 16px;border:2px solid #22c55e;\">Solve Problem</a></td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>
"""

TEXT_TEMPLATE = """WEEKLY CSES\n{problem_name}\nSolve Problem: {problem_url}\n"""


@dataclass
class Problem:
    name: str
    pid: str
    url: str


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def executable_dir() -> Path:
    return Path(__file__).resolve().parent


def resolve_path(value: str, base: Path) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    return (base / p).resolve()


def default_config_path(base: Path, override: str) -> Path:
    if override:
        return resolve_path(override, base)

    for name in ("email_config.local.txt", "email_config.txt", "email_config.example.txt"):
        candidate = base / name
        if candidate.exists():
            return candidate
    return base / "email_config.local.txt"


def load_key_value_config(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    out: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            out[key] = value
    return out


def load_problems(path: Path) -> List[Problem]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"problems file must be a non-empty JSON array: {path}")

    out: List[Problem] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        pid = str(item.get("id", "")).strip()
        url = str(item.get("url", "")).strip()
        if name and pid and url:
            out.append(Problem(name=name, pid=pid, url=url))

    if not out:
        raise ValueError(f"no valid problems found in {path}")
    return out


def load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "next_index": 0,
            "sent_log": [],
            "created_at": now_iso(),
            "updated_at": None,
        }
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"state file must be a JSON object: {path}")
    raw.setdefault("next_index", 0)
    raw.setdefault("sent_log", [])
    return raw


def save_state(path: Path, state: Dict[str, Any]) -> None:
    state["updated_at"] = now_iso()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def normalize_index(idx: int, total: int, wrap: bool) -> int:
    if total <= 0:
        raise ValueError("problem list is empty")
    if wrap:
        return idx % total
    if idx < 0:
        raise ValueError("invalid negative next_index")
    if idx >= total:
        raise ValueError("reached end of problem list and --no-wrap was set")
    return idx


def build_message(sender: str, recipient: str, subject: str, problem: Problem) -> MIMEMultipart:
    msg = MIMEMultipart("alternative")
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(TEXT_TEMPLATE.format(problem_name=problem.name, problem_url=problem.url), "plain"))
    msg.attach(MIMEText(HTML_TEMPLATE.format(problem_name=problem.name, problem_url=problem.url), "html"))
    return msg


def send_email(sender: str, password: str, recipient: str, subject: str, problem: Problem) -> None:
    msg = build_message(sender, recipient, subject, problem)
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, [recipient], msg.as_string())


def main() -> int:
    base = executable_dir()

    parser = argparse.ArgumentParser(description="Sequential CSES sender with persistent state.")
    parser.add_argument("--problems-file", default="problems.json", help="Relative to script dir unless absolute")
    parser.add_argument("--state-file", default="weekly_sender_state.json", help="Relative to script dir unless absolute")
    parser.add_argument(
        "--config-file",
        default="",
        help="key=value file: sender,password,to_email; defaults to email_config.local.txt",
    )
    parser.add_argument("--from-email", default="", help="Override sender")
    parser.add_argument("--app-password", default="", help="Override app password")
    parser.add_argument("--to-email", default="", help="Override recipient")
    parser.add_argument("--subject-prefix", default="WEEKLY CSES: ", help="Subject prefix")
    parser.add_argument("--no-wrap", action="store_true", help="Stop at end of problem list")
    parser.add_argument("--dry-run", action="store_true", help="Do not send, still persist state")
    args = parser.parse_args()

    problems_path = resolve_path(args.problems_file, base)
    state_path = resolve_path(args.state_file, base)
    config_path = default_config_path(base, args.config_file)

    config = load_key_value_config(config_path)
    sender = (args.from_email or os.getenv("GMAIL_USER", "") or config.get("sender", "")).strip()
    password = (args.app_password or os.getenv("GMAIL_APP_PASSWORD", "") or config.get("password", "")).strip()
    recipient = (args.to_email or os.getenv("TO_EMAIL", "") or config.get("to_email", "")).strip()

    problems = load_problems(problems_path)
    state = load_state(state_path)

    idx = normalize_index(int(state.get("next_index", 0)), len(problems), wrap=(not args.no_wrap))
    problem = problems[idx]
    subject = f"{args.subject_prefix}{problem.name}"

    if args.dry_run:
        print(f"[DRY RUN] Would send: {subject} -> {problem.url}")
    else:
        if not sender or not password or not recipient:
            raise SystemExit(
                "missing sender/recipient credentials: set --from-email/--app-password/--to-email "
                "or create email_config.local.txt from email_config.example.txt"
            )
        send_email(sender, password, recipient, subject, problem)
        print(f"Sent: {subject}")

    state.setdefault("sent_log", []).append(
        {
            "sent_at": now_iso(),
            "problem_index": idx,
            "problem_id": problem.pid,
            "problem_name": problem.name,
            "problem_url": problem.url,
            "subject": subject,
        }
    )
    state["next_index"] = idx + 1
    state.setdefault("created_at", now_iso())

    save_state(state_path, state)
    print(f"State updated: {state_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise
