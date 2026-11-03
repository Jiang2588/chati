# -*- coding: utf-8 -*-
"""Rebuild banks/manifest.json from every public bank file."""
import json, os, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANKS = os.path.join(ROOT, "banks")

def main():
    items = []
    for path in sorted(glob.glob(os.path.join(BANKS, "*.json"))):
        name = os.path.basename(path)
        if name == "manifest.json":
            continue
        try:
            with open(path, encoding="utf-8") as f:
                bank = json.load(f)
        except Exception as e:
            print("skip", name, e)
            continue
        questions = bank.get("questions") or []
        items.append({
            "id": bank.get("id") or name[:-5],
            "title": bank.get("title") or name[:-5],
            "subject": bank.get("subject", ""),
            "source": bank.get("source", ""),
            "description": bank.get("description", ""),
            "createdAt": bank.get("createdAt", ""),
            "count": len(questions),
            "file": "banks/" + name,
        })
    with open(os.path.join(BANKS, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"banks": items}, f, ensure_ascii=False, indent=1)
    print(f"manifest: {len(items)} banks, {sum(i['count'] for i in items)} questions")

if __name__ == "__main__":
    main()
