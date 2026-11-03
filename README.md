# 拆题

把教材和课件拆成一题一页。

导入 PDF 或 Word，自动找出编号题目，选择要收进题库的部分，然后按顺序或随机练。每页只放一道题，可以看答案、跳下一题、记错题。

线上地址：https://jiang2588.github.io/chati/

## 它能做什么

- 导入有文字层的 PDF 和 `.docx`，自动切题，识别选择题选项和「答案 / 解析」标记
- 题库分公共和私人：公共题库放在仓库里，任何人都能用；私人题库只在当前浏览器
- 练习时显示来源章节、页码，可收藏、记错题，进度自动保存
- 键盘 `←` `→` 翻题，空格显示答案；手机上可以左右滑
- 公共题库通过 GitHub Issue 表单提交，仓库 Action 自动校验、入库、更新清单

## 已经放进来的公共题库

| 题库 | 题量 | 来源 |
| --- | --- | --- |
| 大学物理 · 教材习题（第 1–10 章） | 332 | Principles of Physics, 10th ed. |
| 高等数学 · 讲义例题全解 | 157 | MA117 讲义例题 Ch02–Ch04 |
| 高等数学 · 期中模拟 A / B 卷 | 16 + 16 | MA117 模拟卷 |
| 高等数学 · 2023 秋期中 | 15 | MA117 2023 期中 |
| 大学物理 · Tutorial 例题 | 15 | 大学物理（一）Tutorial |

教材习题里，原书只给奇数题答案，偶数题会显示「原书没有给答案」。

## 本地运行

```bash
python -m http.server 8087
```

打开 `http://localhost:8087`。不要直接双击 `index.html`：浏览器在 `file://` 下会拦掉 PDF 解析和题库清单。

## 想加一份公共题库

1. 在页面里导入文件、切题、保存为私人题库。
2. 打开仓库的 Issue 表单，把导出的 JSON 粘进去。
3. Action 会自动写进 `banks/` 并更新 `banks/manifest.json`。

单份 JSON 建议不超过 6 万字符，太大就拆成几份。Issue 表单走 GitHub 的账号体系，不用服务器，也不用每个人配 token。

管理员也可以直接在 `banks/` 放 JSON，再跑：

```bash
python tools/build_manifest.py
```

## 目录

```
index.html                 单页应用
vendor/pdf.min.js          PDF.js 3.11
vendor/pdf.worker.min.js
vendor/jszip.min.js        Word 解包
banks/*.json               公共题库
tools/build_manifest.py     重建清单
tools/merge_issue.py        处理 Issue 提交
.github/workflows/         自动合并、重建清单
```

## 限制

- 扫描版 PDF、照片课件没有文字层，读不出字。需要先 OCR 或另存为文字版。
- 旧版 `.doc` 不支持，先在 Word 里另存为 `.docx`。
- 题目切分靠编号和排版规则，编号混乱的资料会有漏题或串题，导入后有预览可以勾选。
- 私人题库存在 IndexedDB / localStorage，清浏览器数据会丢。重要的题库记得导出。
