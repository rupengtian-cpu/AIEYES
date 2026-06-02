#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AIEYES 数据抓取脚本
- 论文来源: arXiv API, 聚焦 "AI 最新数据 / 评测 / Benchmark" 方向, 并附中文要点
- 资讯来源: Google News RSS, 聚焦行业 top 级发展与技术进展 (过滤科普/合作/教程类)
- 输出: data/YYYY-MM-DD.json  以及  data/index.json (日期索引)

仅依赖 Python 标准库, 无需安装第三方包。
用法:
    python3 scripts/fetch_data.py
    python3 scripts/fetch_data.py --papers 12 --news 12
"""

import argparse
import html
import json
import os
import re
import socket
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

USER_AGENT = "Mozilla/5.0 (AIEYES daily aggregator; +https://github.com/)"
TIMEOUT = 30

# arXiv 中 AI 相关分类
ARXIV_CATEGORIES = ["cs.AI", "cs.LG", "cs.CL", "cs.CV", "cs.RO", "cs.NE", "stat.ML"]
# 论文聚焦方向: 数据 / 评测 / 基准
ARXIV_TOPICS = ["benchmark", "evaluation", "dataset", "evaluating", "leaderboard", "benchmarking"]

# AI 资讯 RSS 源 (Google News 聚合, 聚焦行业进展与技术)
NEWS_FEEDS = [
    {
        "lang": "zh",
        "url": "https://news.google.com/rss/search?q="
        + urllib.parse.quote("大模型 OR GPT OR Gemini OR 开源模型 OR AI芯片 OR 算力 OR AI融资 OR 智能体 when:3d")
        + "&hl=zh-CN&gl=CN&ceid=CN:zh",
    },
    {
        "lang": "en",
        "url": "https://news.google.com/rss/search?q="
        + urllib.parse.quote("(OpenAI OR Anthropic OR Google DeepMind OR LLM OR \"AI model\" OR \"AI chip\") (launch OR release OR funding OR breakthrough OR raises) when:3d")
        + "&hl=en-US&gl=US&ceid=US:en",
    },
]

# 工具技能 —— GitHub 热门 AI 工具/Agent/MCP 项目 (自动抓取)
GITHUB_QUERIES = [
    "mcp server in:name,description,topics",
    "ai agent OR agentic in:name,description,topics",
    "llm tool OR llm framework OR rag in:name,description,topics",
]

# 工具技能 —— 精选 Skill / MCP / Agent / 经验资源 (常青内容, 可手动维护)
CURATED_TOOLS = [
    {
        "title": "Model Context Protocol (MCP)",
        "type": "MCP",
        "summary": "Anthropic 提出的开放协议，标准化大模型与外部工具/数据源的连接，是构建 Agent 工具调用能力的基础规范。",
        "url": "https://modelcontextprotocol.io",
        "author": "Anthropic",
        "stars": None,
        "language": "",
    },
    {
        "title": "Awesome MCP Servers",
        "type": "MCP",
        "summary": "社区整理的 MCP Server 大全，涵盖文件、数据库、浏览器、搜索、IDE 等可直接接入 Agent 的工具服务。",
        "url": "https://github.com/punkpeye/awesome-mcp-servers",
        "author": "punkpeye",
        "stars": None,
        "language": "",
    },
    {
        "title": "OpenAI Cookbook",
        "type": "经验",
        "summary": "OpenAI 官方实战示例库，包含函数调用、RAG、Agent、评测等大量可复用的代码与最佳实践。",
        "url": "https://github.com/openai/openai-cookbook",
        "author": "OpenAI",
        "stars": None,
        "language": "",
    },
    {
        "title": "Cursor Directory",
        "type": "Skill",
        "summary": "汇集各类 Cursor Rules / MCP / 技能配置，可直接复用到 AI 编程工作流，提升 Agent 编码效率。",
        "url": "https://cursor.directory",
        "author": "Cursor",
        "stars": None,
        "language": "",
    },
    {
        "title": "Anthropic Agents & Tools 文档",
        "type": "Skill",
        "summary": "Claude 工具调用、Agent 与 Skills 官方指南，讲解如何编排多步骤工具调用、构建可靠 Agent。",
        "url": "https://docs.anthropic.com/en/docs/agents-and-tools/overview",
        "author": "Anthropic",
        "stars": None,
        "language": "",
    },
    {
        "title": "Hugging Face Daily Papers & Spaces",
        "type": "社媒",
        "summary": "每日热门论文与可在线体验的模型 Demo（Spaces），是发现新工具、快速复现前沿成果的高效入口。",
        "url": "https://huggingface.co/papers",
        "author": "Hugging Face",
        "stars": None,
        "language": "",
    },
]

# 工具技能 —— 社媒科普精选 (YouTube/抖音/小红书/B站, 高赞高藏 AI 工具内容入口)
# 抖音/小红书无公开 API, 采用话题/搜索深链直达高互动内容流; YouTube 用头部频道直链。
SOCIAL_TOOLS = [
    {
        "title": "Two Minute Papers (YouTube)",
        "type": "视频",
        "summary": "每期用精美可视化解读最新 AI 论文与工具效果，点赞量极高的科普标杆频道，适合快速 get 前沿成果。",
        "url": "https://www.youtube.com/@TwoMinutePapers",
        "author": "YouTube",
        "stars": None,
        "language": "",
    },
    {
        "title": "Matt Wolfe (YouTube)",
        "type": "视频",
        "summary": "每周盘点最新最热门的 AI 工具并实测演示，高赞高收藏，是跟进 AI 工具生态的高效频道。",
        "url": "https://www.youtube.com/@mreflow",
        "author": "YouTube",
        "stars": None,
        "language": "",
    },
    {
        "title": "Fireship (YouTube)",
        "type": "视频",
        "summary": "高能短视频讲解 AI 与编程工具，节奏快、点赞量爆表，适合碎片时间快速了解新工具。",
        "url": "https://www.youtube.com/@Fireship",
        "author": "YouTube",
        "stars": None,
        "language": "",
    },
    {
        "title": "抖音 ·「AI工具」高赞合集",
        "type": "社媒",
        "summary": "抖音「AI工具」搜索入口，直达高点赞的 AI 工具实测、教程与避坑短视频内容流。",
        "url": "https://www.douyin.com/search/AI%E5%B7%A5%E5%85%B7",
        "author": "抖音",
        "stars": None,
        "language": "",
    },
    {
        "title": "小红书 ·「AI工具」高藏笔记",
        "type": "社媒",
        "summary": "小红书「AI工具」搜索入口，汇集高收藏的 AI 工具种草笔记、效率玩法与实用清单。",
        "url": "https://www.xiaohongshu.com/search_result?keyword=AI%E5%B7%A5%E5%85%B7",
        "author": "小红书",
        "stars": None,
        "language": "",
    },
    {
        "title": "哔哩哔哩 ·「AI工具」高播教程",
        "type": "视频",
        "summary": "B 站「AI工具」搜索入口，覆盖高播放、高三连的 AI 工具深度教程与测评长视频。",
        "url": "https://search.bilibili.com/all?keyword=AI%E5%B7%A5%E5%85%B7",
        "author": "哔哩哔哩",
        "stars": None,
        "language": "",
    },
]

# 资讯过滤: 命中以下关键词的标题视为科普/教程/合作/广告类, 予以剔除
NEWS_BLOCKLIST = [
    "科普", "入门", "教程", "教学", "如何", "怎么", "盘点", "合作", "签约", "携手",
    "招聘", "课程", "培训", "广告", "揭秘", "是什么", "一文", "答疑", "公开课",
    "直播预告", "报名", "活动", "沙龙", "峰会预告", "概念股", "股价", "涨停", "跌停",
    "tutorial", "how to", "how-to", "guide", "beginner", "course", "explained",
    "what is", "what are", "partnership", "hiring", "webinar", "sponsored", "tips",
]


def http_get(url, retries=0, backoff=5.0):
    last_exc = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code == 429 and attempt < retries:
                wait = backoff * (attempt + 1)
                print(f"[info] 429 限流, {wait:.0f}s 后重试 ({attempt + 1}/{retries})", file=sys.stderr)
                time.sleep(wait)
                continue
            raise
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff)
                continue
            raise
    if last_exc:
        raise last_exc


def clean_text(text):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate(text, n=320):
    text = text or ""
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def translate_to_zh(text, retries=2):
    """调用 Google 翻译公开端点把英文转中文, 失败则返回空串。"""
    if not text:
        return ""
    text = text[:1900]
    url = (
        "https://translate.googleapis.com/translate_a/single?client=gtx"
        "&sl=en&tl=zh-CN&dt=t&q=" + urllib.parse.quote(text)
    )
    for attempt in range(retries + 1):
        try:
            raw = http_get(url)
            data = json.loads(raw.decode("utf-8"))
            parts = [seg[0] for seg in data[0] if seg and seg[0]]
            return "".join(parts).strip()
        except Exception:  # noqa: BLE001
            if attempt < retries:
                time.sleep(1.2)
            continue
    return ""


# --------------------------------------------------------------------------- #
# arXiv 论文 (聚焦数据 / 评测 / Benchmark, 附中文要点)
# --------------------------------------------------------------------------- #
def fetch_papers(max_results=12):
    cat_q = "+OR+".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
    topic_q = "+OR+".join(
        [f"abs:{t}" for t in ARXIV_TOPICS] + [f"ti:{t}" for t in ARXIV_TOPICS]
    )
    url = (
        "https://export.arxiv.org/api/query?"
        f"search_query=%28{cat_q}%29+AND+%28{topic_q}%29"
        "&sortBy=submittedDate&sortOrder=descending"
        f"&start=0&max_results={max_results}"
    )
    raw = http_get(url, retries=4, backoff=15.0)
    ns = {"a": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    root = ET.fromstring(raw)
    papers = []
    for entry in root.findall("a:entry", ns):
        title = clean_text(entry.findtext("a:title", default="", namespaces=ns))
        summary = clean_text(entry.findtext("a:summary", default="", namespaces=ns))
        published = entry.findtext("a:published", default="", namespaces=ns)

        authors = [
            clean_text(a.findtext("a:name", default="", namespaces=ns))
            for a in entry.findall("a:author", ns)
        ]
        authors = [a for a in authors if a]

        abs_link = ""
        pdf_link = ""
        for link in entry.findall("a:link", ns):
            if link.get("type") == "application/pdf":
                pdf_link = link.get("href", "")
            elif link.get("rel") == "alternate":
                abs_link = link.get("href", "")

        raw_id = entry.findtext("a:id", default="", namespaces=ns)
        arxiv_id = raw_id.rsplit("/abs/", 1)[-1] if "/abs/" in raw_id else raw_id
        if not pdf_link and arxiv_id:
            pdf_link = f"https://arxiv.org/pdf/{arxiv_id}"
        if not abs_link and arxiv_id:
            abs_link = f"https://arxiv.org/abs/{arxiv_id}"

        primary = entry.find("arxiv:primary_category", ns)
        category = primary.get("term") if primary is not None else ""

        # 中文要点 (标题 + 摘要翻译)
        title_zh = translate_to_zh(title)
        summary_zh = translate_to_zh(summary)

        papers.append(
            {
                "title": title,
                "title_zh": title_zh,
                "summary": truncate(summary, 360),
                "summary_zh": truncate(summary_zh, 380),
                "authors": authors[:6],
                "published": published,
                "category": category,
                "arxiv_id": arxiv_id,
                "abs_url": abs_link,
                "pdf_url": pdf_link,
            }
        )
        time.sleep(0.3)  # 善待翻译端点
    return papers


# --------------------------------------------------------------------------- #
# AI 资讯 (聚焦行业进展与技术, 过滤科普/合作/教程类)
# --------------------------------------------------------------------------- #
def is_blocked(title):
    low = (title or "").lower()
    return any(kw.lower() in low for kw in NEWS_BLOCKLIST)


def fetch_news(max_results=12):
    items = []
    seen_titles = set()
    per_feed = max(8, max_results)

    for feed in NEWS_FEEDS:
        try:
            raw = http_get(feed["url"])
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] 资讯源抓取失败 ({feed['lang']}): {exc}", file=sys.stderr)
            continue
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            print(f"[warn] 资讯源解析失败 ({feed['lang']}): {exc}", file=sys.stderr)
            continue

        channel = root.find("channel")
        if channel is None:
            continue

        count = 0
        for item in channel.findall("item"):
            if count >= per_feed:
                break
            title = clean_text(item.findtext("title", default=""))
            if not title or title in seen_titles:
                continue

            link = (item.findtext("link", default="") or "").strip()
            pub = item.findtext("pubDate", default="")
            desc = clean_text(item.findtext("description", default=""))
            source = ""
            src_el = item.find("source")
            if src_el is not None and src_el.text:
                source = clean_text(src_el.text)
            if not source and " - " in title:
                title, source = title.rsplit(" - ", 1)
                title, source = title.strip(), source.strip()

            if is_blocked(title) or is_blocked(desc):
                continue

            seen_titles.add(title)
            items.append(
                {
                    "title": title,
                    "summary": truncate(desc, 220),
                    "source": source,
                    "lang": feed["lang"],
                    "published": pub,
                    "url": link,
                }
            )
            count += 1

    return items[:max_results] if max_results else items


# --------------------------------------------------------------------------- #
# 工具技能 (GitHub 热门 AI 工具 + 精选资源)
# --------------------------------------------------------------------------- #
def fetch_github_tools(limit=8):
    since = (datetime.now(timezone.utc) - timedelta(days=90)).strftime("%Y-%m-%d")
    out = []
    seen = set()
    per_page = 5
    for q in GITHUB_QUERIES:
        full_q = f"{q} stars:>500 pushed:>{since}"
        url = (
            "https://api.github.com/search/repositories?q="
            + urllib.parse.quote(full_q)
            + f"&sort=stars&order=desc&per_page={per_page}"
        )
        try:
            raw = http_get(url)
            data = json.loads(raw.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] GitHub 工具抓取失败: {exc}", file=sys.stderr)
            continue
        for repo in data.get("items", []):
            name = repo.get("full_name")
            if not name or name in seen:
                continue
            seen.add(name)
            out.append(
                {
                    "title": repo.get("name") or name,
                    "type": "GitHub",
                    "summary_en": (repo.get("description") or "").strip(),
                    "summary": "",
                    "url": repo.get("html_url") or "",
                    "author": (repo.get("owner") or {}).get("login", ""),
                    "stars": repo.get("stargazers_count", 0),
                    "language": repo.get("language") or "",
                }
            )
            if len(out) >= limit:
                break
        if len(out) >= limit:
            break
        time.sleep(1.0)  # 善待 GitHub 搜索接口

    # 英文描述翻译为中文
    for t in out:
        if t["summary_en"]:
            t["summary"] = translate_to_zh(t["summary_en"]) or t["summary_en"]
            time.sleep(0.3)
    return out


def fetch_tools(max_results=18):
    tools = []
    try:
        tools = fetch_github_tools(limit=8)
        print(f"    GitHub 工具: {len(tools)} 个")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] GitHub 工具抓取异常: {exc}", file=sys.stderr)
        tools = []
    # 顺序: GitHub 热门 (动态) -> 社媒科普 (视频/抖音/小红书/B站) -> 精选资源 (常青)
    tools.extend(SOCIAL_TOOLS)
    tools.extend(CURATED_TOOLS)
    return tools[:max_results] if max_results else tools


# --------------------------------------------------------------------------- #
# 写入
# --------------------------------------------------------------------------- #
def update_index(date_str):
    os.makedirs(DATA_DIR, exist_ok=True)
    index_path = os.path.join(DATA_DIR, "index.json")
    dates = []
    if os.path.exists(index_path):
        try:
            with open(index_path, "r", encoding="utf-8") as f:
                dates = json.load(f).get("dates", [])
        except Exception:  # noqa: BLE001
            dates = []
    if date_str not in dates:
        dates.append(date_str)
    dates = sorted(set(dates), reverse=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(
            {"dates": dates, "updated_at": datetime.now(timezone.utc).isoformat()},
            f,
            ensure_ascii=False,
            indent=2,
        )
    return dates


def main():
    parser = argparse.ArgumentParser(description="AIEYES 每日数据抓取")
    parser.add_argument("--papers", type=int, default=12, help="抓取论文数量 (>=10)")
    parser.add_argument("--news", type=int, default=12, help="抓取资讯数量 (>=10)")
    parser.add_argument("--tools", type=int, default=20, help="工具技能数量 (>=10)")
    parser.add_argument("--date", type=str, default=None, help="指定日期 YYYY-MM-DD, 默认今天")
    args = parser.parse_args()

    socket.setdefaulttimeout(TIMEOUT)
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")

    print(f"==> 抓取 {date_str} 的 AI 评测论文 / 行业资讯 / 工具技能 ...")

    try:
        papers = fetch_papers(max(10, args.papers))
        print(f"    论文: {len(papers)} 篇 (聚焦数据/评测/Benchmark)")
    except Exception as exc:  # noqa: BLE001
        print(f"[error] 论文抓取失败: {exc}", file=sys.stderr)
        papers = []

    try:
        news = fetch_news(max(10, args.news))
        print(f"    资讯: {len(news)} 条 (聚焦行业进展与技术)")
    except Exception as exc:  # noqa: BLE001
        print(f"[error] 资讯抓取失败: {exc}", file=sys.stderr)
        news = []

    try:
        tools = fetch_tools(max(10, args.tools))
        print(f"    工具技能: {len(tools)} 个 (GitHub 热门 + 精选资源)")
    except Exception as exc:  # noqa: BLE001
        print(f"[error] 工具技能抓取失败: {exc}", file=sys.stderr)
        tools = []

    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, f"{date_str}.json")

    # 安全兜底: 若本次某一模块抓取为空, 沿用已有文件中的旧数据, 避免覆盖丢失
    if (not papers or not news or not tools) and os.path.exists(out_path):
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                old = json.load(f)
            if not papers and old.get("papers"):
                papers = old["papers"]
                print("[info] 论文沿用已有数据 (本次抓取为空)")
            if not news and old.get("news"):
                news = old["news"]
                print("[info] 资讯沿用已有数据 (本次抓取为空)")
            if not tools and old.get("tools"):
                tools = old["tools"]
                print("[info] 工具技能沿用已有数据 (本次抓取为空)")
        except Exception:  # noqa: BLE001
            pass

    payload = {
        "date": date_str,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "paper_count": len(papers),
        "news_count": len(news),
        "tool_count": len(tools),
        "papers": papers,
        "news": news,
        "tools": tools,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    dates = update_index(date_str)
    print(f"==> 已写入 {out_path}")
    print(f"==> 索引日期共 {len(dates)} 天: {dates[:5]}{' ...' if len(dates) > 5 else ''}")

    if len(papers) < 10 or len(news) < 10:
        print("[warn] 本次抓取数量未达到 10 篇/条, 请检查网络或数据源。", file=sys.stderr)


if __name__ == "__main__":
    main()
