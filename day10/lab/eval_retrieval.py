#!/usr/bin/env python3
"""
Đánh giá retrieval — before/after khi pipeline đổi dữ liệu embed.

Chế độ mặc định: keyword-based (không cần LLM).
Chế độ LLM-judge (--llm-judge): dùng OpenAI GPT để đánh giá chất lượng câu trả lời
  dựa trên context retrieved, cho điểm faithfulness (0/1) và ghi lý do.

Nguyễn Tuấn Khải — Quality/Expectation Owner (LLM-judge extension).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent


def _llm_judge(question: str, context: str, api_key: str, model: str = "gpt-4o-mini") -> dict:
    """
    Gọi OpenAI để đánh giá context retrieved có đủ để trả lời câu hỏi không.
    Trả về {"faithful": bool, "score": int (0|1), "reason": str}.
    """
    try:
        from openai import OpenAI
    except ImportError:
        return {"faithful": False, "score": 0, "reason": "openai package not installed"}

    client = OpenAI(api_key=api_key)
    prompt = f"""Bạn là judge đánh giá chất lượng retrieval trong hệ RAG.

Câu hỏi: {question}

Context được retrieved (top-k chunks ghép lại):
\"\"\"
{context[:2000]}
\"\"\"

Nhiệm vụ: Dựa CHỈ vào context trên, context có chứa đủ thông tin để trả lời chính xác câu hỏi không?

Trả lời theo JSON (chỉ JSON, không giải thích thêm):
{{"faithful": true/false, "score": 1/0, "reason": "lý do ngắn gọn (tối đa 1 câu)"}}"""

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=150,
        )
        raw = resp.choices[0].message.content.strip()
        # Parse JSON từ response
        raw = raw.strip("```json").strip("```").strip()
        return json.loads(raw)
    except Exception as e:
        return {"faithful": False, "score": 0, "reason": f"judge_error: {e}"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--questions",
        default=str(ROOT / "data" / "test_questions.json"),
        help="JSON danh sách câu hỏi golden (retrieval)",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "artifacts" / "eval" / "before_after_eval.csv"),
        help="CSV kết quả",
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument(
        "--llm-judge",
        action="store_true",
        help="Bật LLM-judge (OpenAI) để đánh giá faithfulness context — cần OPENAI_API_KEY trong .env",
    )
    parser.add_argument(
        "--judge-model",
        default="gpt-4o-mini",
        help="Model OpenAI dùng cho LLM-judge (mặc định: gpt-4o-mini)",
    )
    args = parser.parse_args()

    openai_key: Optional[str] = os.environ.get("OPENAI_API_KEY") if args.llm_judge else None
    if args.llm_judge and not openai_key:
        print("ERROR: --llm-judge yêu cầu OPENAI_API_KEY trong .env", file=sys.stderr)
        return 1

    try:
        import chromadb
        from chromadb.utils import embedding_functions
    except ImportError:
        print("Install: pip install chromadb sentence-transformers", file=sys.stderr)
        return 1

    qpath = Path(args.questions)
    if not qpath.is_file():
        print(f"questions not found: {qpath}", file=sys.stderr)
        return 1

    questions = json.loads(qpath.read_text(encoding="utf-8"))
    db_path = os.environ.get("CHROMA_DB_PATH", str(ROOT / "chroma_db"))
    collection_name = os.environ.get("CHROMA_COLLECTION", "day10_kb")
    model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

    client = chromadb.PersistentClient(path=db_path)
    emb = embedding_functions.OpenAIEmbeddingFunction(api_key=os.environ.get("OPENAI_API_KEY"), model_name=model_name)
    try:
        col = client.get_collection(name=collection_name, embedding_function=emb)
    except Exception as e:
        print(f"Collection error: {e}", file=sys.stderr)
        return 2

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    use_llm = args.llm_judge and openai_key

    fieldnames = [
        "question_id",
        "question",
        "top1_doc_id",
        "top1_preview",
        "contains_expected",
        "hits_forbidden",
        "top1_doc_expected",
        "top_k_used",
    ]
    if use_llm:
        fieldnames += ["llm_faithful", "llm_score", "llm_reason"]

    with out_path.open("w", encoding="utf-8", newline="") as fcsv:
        w = csv.DictWriter(fcsv, fieldnames=fieldnames)
        w.writeheader()
        for q in questions:
            text = q["question"]
            res = col.query(query_texts=[text], n_results=args.top_k)
            docs = (res.get("documents") or [[]])[0]
            metas = (res.get("metadatas") or [[]])[0]
            top_doc = (metas[0] or {}).get("doc_id", "") if metas else ""
            preview = (docs[0] or "")[:180].replace("\n", " ") if docs else ""
            blob = " ".join(docs).lower()
            must_any = [x.lower() for x in q.get("must_contain_any", [])]
            forbidden = [x.lower() for x in q.get("must_not_contain", [])]
            ok_any = any(m in blob for m in must_any) if must_any else True
            bad_forb = any(m in blob for m in forbidden) if forbidden else False
            want_top1 = (q.get("expect_top1_doc_id") or "").strip()
            top1_expected = ""
            if want_top1:
                top1_expected = "yes" if top_doc == want_top1 else "no"

            row = {
                "question_id": q.get("id", ""),
                "question": text,
                "top1_doc_id": top_doc,
                "top1_preview": preview,
                "contains_expected": "yes" if ok_any else "no",
                "hits_forbidden": "yes" if bad_forb else "no",
                "top1_doc_expected": top1_expected,
                "top_k_used": args.top_k,
            }

            if use_llm:
                context = "\n---\n".join(docs)
                judge = _llm_judge(text, context, openai_key, model=args.judge_model)
                row["llm_faithful"] = "yes" if judge.get("faithful") else "no"
                row["llm_score"] = judge.get("score", 0)
                row["llm_reason"] = judge.get("reason", "")
                print(f"  [{q.get('id')}] llm_score={row['llm_score']} reason={row['llm_reason']}")

            w.writerow(row)

    print(f"Wrote {out_path}")
    if use_llm:
        print("LLM-judge columns: llm_faithful, llm_score, llm_reason")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
