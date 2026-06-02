# AIEYES · AI 前沿资讯与论文日报

一个简洁的网页（淡蓝色 · 苹果渐变风格），每日聚合 **AI 行业前沿资讯** 与 **最新评测论文（含中文要点与 PDF 下载地址）**，按天维度更新，每天不少于 10 篇论文与 10 条资讯。

- 论文来源：[arXiv API](https://arxiv.org)（`cs.AI` / `cs.LG` / `cs.CL` / `cs.CV` / `cs.RO` / `cs.NE` / `stat.ML`），**聚焦 AI 最新数据 / 评测 / Benchmark 方向**，并自动生成**中文标题与要点**（Google 翻译公开端点）。
- 资讯来源：Google News RSS，**聚焦行业 top 级技术进展与动态**（大模型 / 芯片 / 算力 / 融资 / 智能体等），自动过滤科普、教程、合作、广告类内容。
- 工具技能：**GitHub 热门 AI 工具 / Agent / MCP 项目**（GitHub Search API，按 star 排序、近 90 天活跃，含中文说明、star 数、语言）+ 一份**精选 Skill / MCP / Agent / 经验资源**（常青内容，可在 `scripts/fetch_data.py` 的 `CURATED_TOOLS` 中维护）。
- 前端：纯静态 HTML / CSS / JS，无构建依赖；居中大按钮切换「前沿论文 / 行业资讯 / 工具技能」，内容区收窄聚焦。
- 抓取脚本：纯 Python 标准库，**无需安装任何第三方包**。

## 目录结构

```
AIEYES/
├── index.html              # 网页入口
├── assets/
│   ├── style.css           # 样式（深色简洁主题）
│   └── app.js              # 前端逻辑：加载并渲染数据
├── data/
│   ├── index.json          # 已收录日期索引
│   └── YYYY-MM-DD.json      # 每日数据（论文 + 资讯）
├── scripts/
│   └── fetch_data.py       # 每日抓取脚本
└── .github/workflows/
    └── update.yml          # GitHub Actions 每日自动更新（可选）
```

## 快速开始

### 1. 抓取当天数据

```bash
python3 scripts/fetch_data.py --papers 12 --news 12
```

可选参数：

- `--papers N`：抓取论文数量（最低 10）
- `--news N`：抓取资讯数量（最低 10）
- `--date YYYY-MM-DD`：指定日期（默认今天）

### 2. 本地预览网页

因为页面通过 `fetch` 读取本地 JSON，需用一个本地服务器打开（不能直接双击 `index.html`）：

```bash
python3 -m http.server 8000
```

然后浏览器访问 <http://localhost:8000>。

## 每日自动更新

### 方案 A：本地 cron（macOS / Linux）

每天 11:00 自动抓取：

```bash
crontab -e
# 加入下面一行（请替换为你的实际路径）
0 11 * * * cd /Users/bytedance/Desktop/AIEYES && /usr/bin/python3 scripts/fetch_data.py >> data/cron.log 2>&1
```

### 方案 B：GitHub Actions（推荐，配合 GitHub Pages 免费托管）

仓库已内置 `.github/workflows/update.yml`，每天定时运行抓取脚本并提交新数据。
将仓库的 Pages 指向根目录后，即可获得一个每日自动更新的在线网页。

## 说明

- 数据仅用于学习研究，版权归原作者 / 媒体所有。
- 论文中文要点由机器翻译生成，仅供快速浏览参考，准确表述请以原文 PDF 为准。
- **arXiv 限流**：短时间内频繁请求 arXiv 会返回 `429 Rate exceeded`。脚本已内置退避重试；若仍失败，等待几分钟后重跑即可（抓取失败时会自动沿用已有数据，不会清空）。

Copyright © Tian Rupeng. All rights reserved.
