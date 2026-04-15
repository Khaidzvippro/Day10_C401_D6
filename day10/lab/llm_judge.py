#!/usr/bin/env python3
"""
LLM judge cho kết quả retrieval (Day 10 lab).

Muc tieu:
- Doc file eval CSV (tu eval_retrieval.py)
- Goi LLM de danh gia factuality/safety theo tung cau hoi
- Xuat JSONL + CSV de nop artifact

Vi du:
  python llm_judge.py \
    --eval-csv artifacts/eval/after_clean_eval.csv \
    --questions data/test_questions.json \
    --out-jsonl artifacts/eval/llm_judge_after_clean.jsonl \
    --out-csv artifacts/eval/llm_judge_after_clean.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parent


def _load_questions(path: Path) -> Dict[str, Dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    out: Dict[str, Dict[str, Any]] = {}
    for row in raw:
        qid = (row.get("id") or "").strip()
        if qid:
            out[qid] = row
    return out


def _load_eval_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _safe_json_loads(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else {"raw_output": text}
    except json.JSONDecodeError:
        return {"raw_output": text, "parse_error": True}


def _build_prompt(eval_row: Dict[str, str], qmeta: Dict[str, Any]) -> str:
    must_contain = qmeta.get("must_contain_any", []) or []
    must_not = qmeta.get("must_not_contain", []) or []
    return (
        "# Role\n"
        "Ban la evaluator nghiem ngat cho he retrieval noi bo.\n\n"
        "# Task\n"
        "Danh gia chat luong retrieval dua tren cau hoi, top1_preview, va keyword policy.\n\n"
        "# Input\n"
        f"- question_id: {eval_row.get('question_id', '')}\n"
        f"- question: {eval_row.get('question', '')}\n"
        f"- top1_doc_id: {eval_row.get('top1_doc_id', '')}\n"
        f"- top1_preview: {eval_row.get('top1_preview', '')}\n"
        f"- must_contain_any: {json.dumps(must_contain, ensure_ascii=False)}\n"
        f"- must_not_contain: {json.dumps(must_not, ensure_ascii=False)}\n\n"
        "# Evaluation rules\n"
        "- factuality_pass: true neu thong tin top1_preview tra loi dung cau hoi.\n"
        "- policy_safe: true neu top1_preview khong vi pham rang buoc policy.\n"
        "- contains_expected: true neu co it nhat 1 keyword trong must_contain_any.\n"
        "- hits_forbidden: true neu co bat ky keyword nao trong must_not_contain.\n"
        "- score_0_to_5: diem tong hop 0-5 (5 la tot nhat).\n"
        '- reason: 1-2 cau ngan, ro ly do danh gia.\n\n'
        "# Output format (strict)\n"
        "Chi tra ve 1 JSON object hop le, KHONG them text ngoai JSON, theo schema:\n"
        "```json\n"
        "{\n"
        '  "factuality_pass": true,\n'
        '  "policy_safe": true,\n'
        '  "contains_expected": true,\n'
        '  "hits_forbidden": false,\n'
        '  "score_0_to_5": 5,\n'
        '  "reason": "1-2 cau ngan"\n'
        "}\n"
        "```\n"
    )


def _call_openai_responses(*, model: str, api_key: str, prompt: str, timeout_s: int) -> Dict[str, Any]:
    url = "https://api.openai.com/v1/responses"
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [{"type": "input_text", "text": prompt}],
            }
        ],
        "text": {"format": {"type": "json_object"}},
    }
    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    parsed = json.loads(body)
    # responses API thuong co output_text da flatten.
    text_out = parsed.get("output_text") or ""
    if not text_out:
        # fallback extract
        parts = parsed.get("output") or []
        chunks: List[str] = []
        for item in parts:
            for c in item.get("content", []) or []:
                t = c.get("text")
                if t:
                    chunks.append(t)
        text_out = "\n".join(chunks).strip()
    return _safe_json_loads(text_out)


def main() -> int:
    p = argparse.ArgumentParser(description="LLM judge for retrieval eval CSV")
    p.add_argument(
        "--eval-csv",
        default=str(ROOT / "artifacts" / "eval" / "after_clean_eval.csv"),
        help="File CSV sinh tu eval_retrieval.py",
    )
    p.add_argument(
        "--questions",
        default=str(ROOT / "data" / "test_questions.json"),
        help="JSON cau hoi de lay must_contain/must_not_contain",
    )
    p.add_argument(
        "--out-jsonl",
        default=str(ROOT / "artifacts" / "eval" / "llm_judge_results.jsonl"),
        help="JSONL ket qua theo tung question",
    )
    p.add_argument(
        "--out-csv",
        default=str(ROOT / "artifacts" / "eval" / "llm_judge_results.csv"),
        help="CSV tong hop ket qua",
    )
    p.add_argument(
        "--model",
        default=os.environ.get("LLM_JUDGE_MODEL", "gpt-4.1-mini"),
        help="Model dung de judge",
    )
    p.add_argument("--timeout", type=int, default=60, help="Timeout moi request (giay)")
    args = p.parse_args()

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: Missing OPENAI_API_KEY in environment/.env", file=sys.stderr)
        return 1

    eval_path = Path(args.eval_csv)
    q_path = Path(args.questions)
    if not eval_path.is_file():
        print(f"ERROR: eval csv not found: {eval_path}", file=sys.stderr)
        return 1
    if not q_path.is_file():
        print(f"ERROR: questions not found: {q_path}", file=sys.stderr)
        return 1

    eval_rows = _load_eval_csv(eval_path)
    qmap = _load_questions(q_path)

    out_jsonl = Path(args.out_jsonl)
    out_csv = Path(args.out_csv)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    out_csv.parent.mkdir(parents=True, exist_ok=True)

    merged_rows: List[Dict[str, Any]] = []
    with out_jsonl.open("w", encoding="utf-8") as fj:
        for row in eval_rows:
            qid = (row.get("question_id") or "").strip()
            qmeta = qmap.get(qid, {})
            prompt = _build_prompt(row, qmeta)
            try:
                judge = _call_openai_responses(
                    model=args.model,
                    api_key=api_key,
                    prompt=prompt,
                    timeout_s=args.timeout,
                )
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="replace")
                judge = {"error": f"http_{e.code}", "detail": detail}
            except Exception as e:
                judge = {"error": "request_failed", "detail": str(e)}

            rec = {
                "question_id": qid,
                "question": row.get("question", ""),
                "top1_doc_id": row.get("top1_doc_id", ""),
                "top1_preview": row.get("top1_preview", ""),
                "retrieval_contains_expected": row.get("contains_expected", ""),
                "retrieval_hits_forbidden": row.get("hits_forbidden", ""),
                "judge_factuality_pass": judge.get("factuality_pass"),
                "judge_policy_safe": judge.get("policy_safe"),
                "judge_contains_expected": judge.get("contains_expected"),
                "judge_hits_forbidden": judge.get("hits_forbidden"),
                "judge_score_0_to_5": judge.get("score_0_to_5"),
                "judge_reason": judge.get("reason", ""),
                "judge_raw": json.dumps(judge, ensure_ascii=False),
                "model": args.model,
            }
            merged_rows.append(rec)
            fj.write(json.dumps(rec, ensure_ascii=False) + "\n")

    fieldnames = [
        "question_id",
        "question",
        "top1_doc_id",
        "retrieval_contains_expected",
        "retrieval_hits_forbidden",
        "judge_factuality_pass",
        "judge_policy_safe",
        "judge_contains_expected",
        "judge_hits_forbidden",
        "judge_score_0_to_5",
        "judge_reason",
        "model",
    ]
    with out_csv.open("w", encoding="utf-8", newline="") as fc:
        w = csv.DictWriter(fc, fieldnames=fieldnames)
        w.writeheader()
        for r in merged_rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    print(f"Wrote {out_jsonl}")
    print(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

