// AIEYES 前端逻辑：加载日期索引 -> 加载某日数据 -> 渲染论文/资讯
(function () {
  "use strict";

  const state = {
    dates: [],
    current: null,
    data: null,
    tab: "papers",
    query: "",
  };

  const $ = (sel) => document.querySelector(sel);

  const els = {
    dateSelect: $("#dateSelect"),
    updatedAt: $("#updatedAt"),
    paperNum: $("#paperNum"),
    newsNum: $("#newsNum"),
    toolNum: $("#toolNum"),
    dayNum: $("#dayNum"),
    loading: $("#loading"),
    empty: $("#empty"),
    papersPanel: $("#papersPanel"),
    newsPanel: $("#newsPanel"),
    toolsPanel: $("#toolsPanel"),
    papersList: $("#papersList"),
    newsList: $("#newsList"),
    toolsList: $("#toolsList"),
    searchInput: $("#searchInput"),
  };

  function escapeHtml(s) {
    return (s || "").replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[c]));
  }

  function fmtDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleString("zh-CN", {
      year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
    });
  }

  function fmtDateShort(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    if (isNaN(d)) return iso;
    return d.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
  }

  async function loadIndex() {
    try {
      const res = await fetch("data/index.json?_=" + Date.now());
      if (!res.ok) throw new Error("index.json 不存在");
      const json = await res.json();
      state.dates = json.dates || [];
    } catch (e) {
      state.dates = [];
    }

    els.dayNum.textContent = state.dates.length || "0";

    if (!state.dates.length) {
      showEmpty();
      return;
    }

    els.dateSelect.innerHTML = state.dates
      .map((d) => `<option value="${d}">${d}</option>`)
      .join("");
    state.current = state.dates[0];
    els.dateSelect.value = state.current;
    await loadDay(state.current);
  }

  async function loadDay(date) {
    els.loading.classList.remove("hidden");
    els.empty.classList.add("hidden");
    try {
      const res = await fetch(`data/${date}.json?_=` + Date.now());
      if (!res.ok) throw new Error("数据不存在");
      state.data = await res.json();
    } catch (e) {
      state.data = null;
      showEmpty();
      return;
    }
    els.loading.classList.add("hidden");
    els.paperNum.textContent = state.data.paper_count ?? (state.data.papers || []).length;
    els.newsNum.textContent = state.data.news_count ?? (state.data.news || []).length;
    if (els.toolNum) els.toolNum.textContent = state.data.tool_count ?? (state.data.tools || []).length;
    els.updatedAt.textContent = "更新于 " + fmtDate(state.data.generated_at);
    render();
  }

  function showEmpty() {
    els.loading.classList.add("hidden");
    els.empty.classList.remove("hidden");
    els.papersList.innerHTML = "";
    els.newsList.innerHTML = "";
    if (els.toolsList) els.toolsList.innerHTML = "";
    els.paperNum.textContent = "0";
    els.newsNum.textContent = "0";
    if (els.toolNum) els.toolNum.textContent = "0";
  }

  function matchQuery(text) {
    if (!state.query) return true;
    return (text || "").toLowerCase().includes(state.query.toLowerCase());
  }

  // arXiv 分类 -> 图标 + 渐变配色
  const CAT_ICONS = {
    "cs.CV": { icon: "👁️", c1: "#5ea8ff", c2: "#22d3ee" },
    "cs.CL": { icon: "💬", c1: "#6ec6ff", c2: "#36c6a8" },
    "cs.LG": { icon: "📈", c1: "#8b5cf6", c2: "#5ea8ff" },
    "cs.AI": { icon: "🤖", c1: "#3b82f6", c2: "#8be0ff" },
    "cs.RO": { icon: "🦾", c1: "#22d3ee", c2: "#5ea8ff" },
    "cs.NE": { icon: "🧠", c1: "#a78bfa", c2: "#6ec6ff" },
    "stat.ML": { icon: "📊", c1: "#36c6a8", c2: "#6ec6ff" },
  };

  function catIcon(cat) {
    return CAT_ICONS[cat] || { icon: "✨", c1: "#5ea8ff", c2: "#a7f3e0" };
  }

  // 资讯关键词 -> 图标
  function newsIcon(text) {
    const t = (text || "").toLowerCase();
    const rules = [
      [/(芯片|chip|gpu|nvidia|英伟达)/, "🔧", "#5ea8ff", "#22d3ee"],
      [/(算力|compute|data ?center|数据中心)/, "⚡", "#8b5cf6", "#5ea8ff"],
      [/(融资|funding|raise|investment|投资|估值|valuation)/, "💰", "#36c6a8", "#6ec6ff"],
      [/(开源|open ?source|发布|release|launch|推出|上线)/, "🚀", "#3b82f6", "#8be0ff"],
      [/(模型|model|gpt|gemini|llm|claude)/, "🧠", "#a78bfa", "#6ec6ff"],
      [/(智能体|agent|机器人|robot)/, "🤖", "#22d3ee", "#5ea8ff"],
    ];
    for (const [re, icon, c1, c2] of rules) {
      if (re.test(t)) return { icon, c1, c2 };
    }
    return { icon: "📰", c1: "#5ea8ff", c2: "#a7f3e0" };
  }

  function paperCard(p) {
    const authors = (p.authors || []).join(", ");
    const titleMain = p.title_zh || p.title;
    const showEnTitle = p.title_zh && p.title && p.title_zh !== p.title;
    const points = p.summary_zh || p.summary;
    const ic = catIcon(p.category);
    return `
      <article class="card paper-card">
        <div class="card-icon" style="--c1:${ic.c1};--c2:${ic.c2}">${ic.icon}</div>
        <div class="card-body">
          <div class="card-top">
            <span class="badge">${escapeHtml(p.category || "AI")}</span>
            <span class="card-meta">${fmtDate(p.published)}${p.arxiv_id ? " · arXiv:" + escapeHtml(p.arxiv_id) : ""}</span>
          </div>
          <h3><a href="${escapeHtml(p.abs_url)}" target="_blank" rel="noopener">${escapeHtml(titleMain)}</a></h3>
          ${showEnTitle ? `<span class="title-en">${escapeHtml(p.title)}</span>` : ""}
          <p class="summary clamp-3">${escapeHtml(points)}</p>
          ${authors ? `<p class="authors">${escapeHtml(authors)}</p>` : ""}
          <div class="card-actions">
            <a class="btn primary" href="${escapeHtml(p.pdf_url)}" target="_blank" rel="noopener">⬇ PDF</a>
            <a class="btn" href="${escapeHtml(p.abs_url)}" target="_blank" rel="noopener">详情</a>
          </div>
        </div>
      </article>`;
  }

  // 工具类型 -> 图标 + 配色
  const TOOL_ICONS = {
    GitHub: { icon: "🐙", c1: "#5d6b86", c2: "#8b5cf6" },
    MCP: { icon: "🔌", c1: "#8b5cf6", c2: "#5ea8ff" },
    Skill: { icon: "🧩", c1: "#3b82f6", c2: "#22d3ee" },
    经验: { icon: "📘", c1: "#36c6a8", c2: "#6ec6ff" },
    社媒: { icon: "📱", c1: "#22d3ee", c2: "#a7f3e0" },
    视频: { icon: "🎬", c1: "#a78bfa", c2: "#5ea8ff" },
    文章: { icon: "📝", c1: "#5ea8ff", c2: "#36c6a8" },
  };

  function toolIcon(type) {
    return TOOL_ICONS[type] || { icon: "🧰", c1: "#5ea8ff", c2: "#a7f3e0" };
  }

  function formatStars(n) {
    if (!n) return "";
    return n >= 1000 ? (n / 1000).toFixed(1).replace(/\.0$/, "") + "k" : String(n);
  }

  function toolCard(t) {
    const ic = toolIcon(t.type);
    const summary = t.summary || t.summary_en || "";
    const meta = [];
    if (t.author) meta.push(escapeHtml(t.author));
    if (t.stars) meta.push("⭐ " + formatStars(t.stars));
    if (t.language) meta.push(escapeHtml(t.language));
    return `
      <article class="card tool-card">
        <div class="card-icon" style="--c1:${ic.c1};--c2:${ic.c2}">${ic.icon}</div>
        <div class="card-body">
          <div class="card-top">
            <span class="badge tool">${escapeHtml(t.type || "工具")}</span>
            ${meta.length ? `<span class="card-meta">${meta.join(" · ")}</span>` : ""}
          </div>
          <h3><a href="${escapeHtml(t.url)}" target="_blank" rel="noopener">${escapeHtml(t.title)}</a></h3>
          ${summary ? `<p class="summary clamp-2">${escapeHtml(summary)}</p>` : ""}
          <a class="news-link" href="${escapeHtml(t.url)}" target="_blank" rel="noopener">前往 →</a>
        </div>
      </article>`;
  }

  function newsCard(n) {
    const ic = newsIcon(n.title + " " + (n.summary || ""));
    return `
      <article class="card news-card">
        <div class="card-icon sm" style="--c1:${ic.c1};--c2:${ic.c2}">${ic.icon}</div>
        <div class="card-body">
          <div class="card-top">
            <span class="badge news">${escapeHtml(n.source || (n.lang === "zh" ? "中文资讯" : "EN News"))}</span>
            <span class="card-meta">${fmtDate(n.published)}</span>
          </div>
          <h3 class="news-title"><a href="${escapeHtml(n.url)}" target="_blank" rel="noopener">${escapeHtml(n.title)}</a></h3>
          ${n.summary ? `<p class="summary clamp-2">${escapeHtml(n.summary)}</p>` : ""}
          <a class="news-link" href="${escapeHtml(n.url)}" target="_blank" rel="noopener">阅读原文 →</a>
        </div>
      </article>`;
  }

  function render() {
    if (!state.data) return;
    const papers = (state.data.papers || []).filter(
      (p) =>
        matchQuery(p.title) ||
        matchQuery(p.title_zh) ||
        matchQuery(p.summary) ||
        matchQuery(p.summary_zh) ||
        matchQuery((p.authors || []).join(" "))
    );
    const news = (state.data.news || []).filter(
      (n) => matchQuery(n.title) || matchQuery(n.summary) || matchQuery(n.source)
    );
    const tools = (state.data.tools || []).filter(
      (t) =>
        matchQuery(t.title) ||
        matchQuery(t.summary) ||
        matchQuery(t.summary_en) ||
        matchQuery(t.type) ||
        matchQuery(t.author)
    );

    els.papersList.innerHTML = papers.length
      ? papers.map(paperCard).join("")
      : `<div class="empty">没有匹配的论文。</div>`;
    els.newsList.innerHTML = news.length
      ? news.map(newsCard).join("")
      : `<div class="empty">没有匹配的资讯。</div>`;
    if (els.toolsList) {
      els.toolsList.innerHTML = tools.length
        ? tools.map(toolCard).join("")
        : `<div class="empty">没有匹配的工具技能。</div>`;
    }

    els.papersPanel.classList.toggle("hidden", state.tab !== "papers");
    els.newsPanel.classList.toggle("hidden", state.tab !== "news");
    if (els.toolsPanel) els.toolsPanel.classList.toggle("hidden", state.tab !== "tools");
  }

  function bindEvents() {
    els.dateSelect.addEventListener("change", (e) => {
      state.current = e.target.value;
      loadDay(state.current);
    });

    document.querySelectorAll(".big-tab").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".big-tab").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        state.tab = btn.dataset.tab;
        render();
      });
    });

    const yearEl = document.getElementById("year");
    if (yearEl) yearEl.textContent = new Date().getFullYear();

    let timer = null;
    els.searchInput.addEventListener("input", (e) => {
      clearTimeout(timer);
      timer = setTimeout(() => {
        state.query = e.target.value.trim();
        render();
      }, 150);
    });
  }

  bindEvents();
  loadIndex();
})();
