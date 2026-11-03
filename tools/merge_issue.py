# -*- coding: utf-8 -*-
"""Turn an issue-form submission into a public bank file."""
import json, os, re, sys

BODY = os.environ.get("ISSUE_BODY", "")
NUM = os.environ.get("ISSUE_NUMBER", "0")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "banks")

def section(title):
    m = re.search(r"###\s*" + re.escape(title) + r"\s*\n(.*?)(?=\n###\s|\Z)", BODY, re.S)
    return m.group(1).strip() if m else ""

def clean_json(raw):
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()

def main():
    name = section("题库名称") or f"公共题库 #{NUM}"
    subject = section("学科") or "其他"
    source = section("来源") or "GitHub 提交"
    raw = clean_json(section("题库 JSON"))
    if not raw:
        print("no json field", file=sys.stderr)
        sys.exit(1)
    try:
        bank = json.loads(raw)
    except Exception as e:
        print("invalid json: %s" % e, file=sys.stderr)
        sys.exit(1)
    questions = bank.get("questions") or []
    if not isinstance(questions, list) or not questions:
        print("questions is empty", file=sys.stderr)
        sys.exit(1)
    if len(questions) > 3000:
        print("too many questions", file=sys.stderr)
        sys.exit(1)
    clean = []
    for i, q in enumerate(questions):
        if not isinstance(q, dict) or not str(q.get("stem", "")).strip():
            continue
        q["id"] = q.get("id") or f"q-{i+1:04d}"
        q["options"] = q.get("options") if isinstance(q.get("options"), list) else []
        q["answer"] = q.get("answer") or ""
        q["explanation"] = q.get("explanation") or ""
        q["type"] = q.get("type") or "short"
        q["chapter"] = q.get("chapter") or "未分章"
        clean.append(q)
    if not clean:
        print("no valid question", file=sys.stderr)
        sys.exit(1)
    out = {
        "id": f"submitted-{NUM}",
        "title": name[:80],
        "subject": subject[:40],
        "source": source[:120],
        "description": f"通过 Issue #{NUM} 提交，共 {len(clean)} 题。",
        "visibility": "public",
        "createdAt": os.environ.get("COMMIT_DATE", "")[:10],
        "count": len(clean),
        "questions": clean,
    }
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"submitted-{NUM}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {path} ({len(clean)} questions)")

if __name__ == "__main__":
    main()
