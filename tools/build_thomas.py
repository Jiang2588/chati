# -*- coding: utf-8 -*-
"""Rebuild the Thomas workbook bank from the source .docx.

Word 里的公式是 OMML，直接抽文字会把分数、指数压平成 a/b、x^2，分组信息全丢。
这里在转换阶段就把结构写成 \frac{分子}{分母}、x^{指数}、lim_{下标}，前端再渲染成
真正的上下分数，避免靠正则去猜分子分母到哪结束。

用法：py -3 tools/build_thomas.py <docx路径> [输出json]
"""
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def conv(el, out):
    tag = el.tag
    if tag == M + "f":
        num = den = ""
        for ch in el:
            if ch.tag == M + "num":
                num = tree(ch)
            elif ch.tag == M + "den":
                den = tree(ch)
        if not num.strip() and not den.strip():
            return
        if not num.strip():
            out.append(den)
            return
        if not den.strip():
            out.append(num)
            return
        out.append("\\frac{%s}{%s}" % (num, den))
        return
    if tag == M + "sSup":
        e = sup = ""
        for ch in el:
            if ch.tag == M + "e":
                e = tree(ch)
            elif ch.tag == M + "sup":
                sup = tree(ch)
        out.append("%s^{%s}" % (e, sup))
        return
    if tag == M + "sSub":
        e = sub = ""
        for ch in el:
            if ch.tag == M + "e":
                e = tree(ch)
            elif ch.tag == M + "sub":
                sub = tree(ch)
        out.append("%s_{%s}" % (e, sub))
        return
    if tag == M + "sSubSup":
        e = sub = sup = ""
        for ch in el:
            if ch.tag == M + "e":
                e = tree(ch)
            elif ch.tag == M + "sub":
                sub = tree(ch)
            elif ch.tag == M + "sup":
                sup = tree(ch)
        out.append("%s_{%s}^{%s}" % (e, sub, sup))
        return
    if tag == M + "rad":
        deg = e = ""
        for ch in el:
            if ch.tag == M + "deg":
                deg = tree(ch)
            elif ch.tag == M + "e":
                e = tree(ch)
        d = deg.strip()
        if not d:
            out.append("√(%s)" % e)
        elif d == "3":
            out.append("∛(%s)" % e)
        elif d == "4":
            out.append("∜(%s)" % e)
        else:
            out.append("√[%s](%s)" % (d, e))
        return
    if tag == M + "d":
        beg = end = ""
        for pr in el.iter(M + "dPr"):
            for ch in pr:
                if ch.tag == M + "begChr":
                    beg = ch.get(M + "val", "")
                elif ch.tag == M + "endChr":
                    end = ch.get(M + "val", "")
        inner = "".join(tree(ch) for ch in el.iter(M + "e"))
        out.append("%s%s%s" % (beg or "(", inner, end or ")"))
        return
    if tag == M + "eqArr":
        rows = [tree(r) for r in el if r.tag == M + "e"]
        out.append("\n".join(r for r in rows if r.strip()))
        return
    if tag == M + "limLow":
        e = lim = ""
        for ch in el:
            if ch.tag == M + "e":
                e = tree(ch)
            elif ch.tag == M + "lim":
                lim = tree(ch)
        out.append("%s_{%s}" % (e, lim))
        return
    if tag == M + "nary":
        chr_ = "∫"
        for pr in el.iter(M + "naryPr"):
            for ch in pr:
                if ch.tag == M + "chr":
                    chr_ = ch.get(M + "val", chr_)
        sub = sup = e = ""
        for ch in el:
            if ch.tag == M + "sub":
                sub = tree(ch)
            elif ch.tag == M + "sup":
                sup = tree(ch)
            elif ch.tag == M + "e":
                e = tree(ch)
        out.append("%s%s%s%s" % (chr_, ("_{%s}" % sub) if sub else "",
                                 ("^{%s}" % sup) if sup else "", e))
        return
    if tag == M + "func":
        name = arg = ""
        for ch in el:
            if ch.tag == M + "fName":
                name = tree(ch)
            elif ch.tag == M + "e":
                arg = tree(ch)
        out.append("%s%s" % (name, arg))
        return
    if tag == M + "r":
        for t in el.iter(M + "t"):
            out.append(t.text or "")
        return
    for ch in el:
        conv(ch, out)


def tree(el):
    out = []
    conv(el, out)
    return "".join(out)


def para_text(p):
    out = []

    def walk(node):
        for ch in node:
            if ch.tag == W + "r":
                for t in ch:
                    if t.tag == W + "t":
                        out.append(t.text or "")
                    elif t.tag == W + "br":
                        out.append("\n")
                    elif t.tag == W + "tab":
                        out.append("\t")
                for t in ch:
                    if t.tag == M + "oMath":
                        conv(t, out)
            elif ch.tag in (M + "oMath", M + "oMathPara"):
                conv(ch, out)
            elif ch.tag in (W + "hyperlink", W + "ins", W + "smartTag",
                            W + "sdt", W + "sdtContent"):
                walk(ch)
            elif ch.tag == W + "p":
                walk(ch)

    walk(p)
    return "".join(out)


def paragraphs(path):
    z = zipfile.ZipFile(path)
    root = ET.fromstring(z.read("word/document.xml"))
    body = root.find(W + "body")
    return [para_text(p) for p in body.iter(W + "p")]


CH_RE = re.compile(r"^第\s*([0-9]+)\s*章\s*(.*?)$")
Q_RE = re.compile(r"^([0-9]+)\.[\u3000\s]+(.+)$", re.S)
SUB_RE = re.compile(r"^[(（][0-9]+[)）]")
OPT_RE = re.compile(r"（[A-D]）")
ANS_RE = re.compile(r"答案[：:]\s*([A-D])")


def cut_solution(text):
    """小问段落里题面和解答常在同一段，切掉解答部分。

    规则：第一个句号之前算题面；若题面里已经有等号把解答写在后面，就在等号处断开。
    跳过 \frac{..}{..}、_{..}、^{..} 花括号里的符号，免得被分母里的 = 骗到。
    """
    depth = 0
    eq = -1
    for i, ch in enumerate(text):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif ch == "=" and depth == 0 and i > 0:
            eq = i
            break
    dot = text.find("。")
    cut = dot + 1 if dot >= 0 else len(text)
    if eq >= 0 and eq < cut:
        # 等号前面太短说明是题面里的赋值，不动
        if len(text[:eq].strip()) > 12:
            cut = eq
    head = text[:cut].rstrip("，、;； ")
    rest = text[cut:].strip()
    return head, rest


def build(path):
    paras = [p.strip("\u200b") for p in paragraphs(path)]
    chapter = ""
    chapter_label = ""
    items = []
    cur = None

    def flush():
        if cur:
            items.append(cur)

    for raw in paras:
        t = raw.strip()
        if not t:
            continue
        m = CH_RE.match(t)
        if m:
            flush()
            cur = None
            chapter = m.group(1)
            chapter_label = "第%s章 %s" % (chapter, m.group(2).strip())
            continue
        m = Q_RE.match(t)
        if m and not SUB_RE.match(t):
            flush()
            num = int(m.group(1))
            body = m.group(2)
            cur = {
                "no": num,
                "body": body,
                "extra": [],
                "answer": [],
                "letter": "",
                "chapter": chapter,
                "chapter_label": chapter_label,
            }
            continue
        if cur is None:
            continue
        am = ANS_RE.search(t)
        if am:
            cur["letter"] = am.group(1)
            before = t[:am.start()].strip()
            after = t[am.end():].strip()
            if before:
                cur["answer"].append(before)
            if after:
                cur["answer"].append(after)
            continue
        if SUB_RE.match(t):
            head, rest = cut_solution(t)
            if head:
                cur["extra"].append(head)
            if rest:
                cur["answer"].append(SUB_RE.match(t).group(0) + " " + rest)
            continue
        cur["answer"].append(t)
    flush()

    questions = []
    for it in items:
        body = it["body"]
        opts = []
        lines = body.split("\n")
        opt_at = next((i for i, l in enumerate(lines) if OPT_RE.search(l)), None)
        if opt_at is not None:
            line = lines[opt_at]
            idx = OPT_RE.search(line).start()
            stem_head = [x for x in lines[:opt_at] if x.strip()]
            if line[:idx].strip():
                stem_head.append(line[:idx].strip())
            stem_parts = stem_head
            opt_text = "\n".join([line[idx:]] + lines[opt_at + 1:])
            for k, txt in re.findall(r"（([A-D])）([^（]*)", opt_text):
                txt = re.sub(r"[\s；;。]+$", "", txt.strip())
                opts.append({"key": k, "text": txt})
        else:
            stem_parts = [x.strip() for x in lines if x.strip()]
        stem_parts.extend(it["extra"])
        stem = "\n".join(stem_parts)

        ans = "\n".join(x for x in it["answer"] if x)
        qtype = "choice" if len(opts) >= 2 else "short"
        if qtype == "choice":
            answer = it["letter"] or "?"
            explanation = ans
        else:
            answer = ans
            explanation = ""

        chapter_no = it["chapter"]
        chapter_label = it["chapter_label"]
        qid = "tw-%s-%02d" % (chapter_no, it["no"])
        questions.append({
            "id": qid,
            "stem": stem,
            "options": opts,
            "answer": answer,
            "explanation": explanation,
            "type": qtype,
            "chapter": chapter_label or ("第%s章" % chapter_no),
            "section": "第%d题" % it["no"],
            "source": "MA117 习题解答（第2–5章）· 第%s章第%d题" % (chapter_no, it["no"]),
        })

    return {
        "id": "thomas-workbook-ch2-5",
        "title": "Thomas 微积分练习册 · 第 2–5 章",
        "subject": "高等数学 MA117",
        "source": "MA117_第2-5章习题解答（一题一答案）.docx",
        "description": "Workbook for Thomas' Calculus 第 2–5 章，共 %d 题，题目与答案解析分开，逐题配对。" % len(questions),
        "visibility": "public",
        "createdAt": "2026-11-03",
        "count": len(questions),
        "questions": questions,
    }


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else "banks/thomas-workbook-ch2-5.json"
    bank = build(src)
    from collections import Counter
    print("questions", len(bank["questions"]), Counter(q["type"] for q in bank["questions"]))
    print("by chapter", Counter(q["chapter"] for q in bank["questions"]))
    no_ans = [q["id"] for q in bank["questions"] if not q["answer"].strip()]
    print("missing answer", no_ans)
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(bank, f, ensure_ascii=False, indent=1)
    print("wrote", dst)


if __name__ == "__main__":
    main()
