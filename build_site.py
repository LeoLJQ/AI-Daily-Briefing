"""
AI Daily Briefing — Static Site Builder

Reads all markdown briefings from daily-briefings/ and generates a single
self-contained index.html with sidebar navigation and rendered content.
No dependencies outside Python stdlib. No internet required to view.
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime

# Fix Windows GBK encoding issues
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent
BRIEFINGS_DIR = ROOT / "daily-briefings"
OUTPUT = ROOT / "index.html"


# ── Markdown parser ──────────────────────────────────────────────────────────

def parse_markdown(text: str) -> str:
    """Convert markdown to HTML. Handles the subset used in our briefings."""

    lines = text.split("\n")
    out = []
    in_list = False
    in_table = False
    in_blockquote = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Horizontal rule
        if re.match(r"^---\s*$", line):
            if in_list:
                out.append("</ul>")
                in_list = False
            if in_blockquote:
                out.append("</blockquote>")
                in_blockquote = False
            out.append("<hr>")
            i += 1
            continue

        # Blockquote
        bq_match = re.match(r"^>\s?(.*)", line)
        if bq_match:
            if not in_blockquote:
                out.append("<blockquote>")
                in_blockquote = True
            # Collect continuation lines
            bq_lines = []
            while i < len(lines) and re.match(r"^>\s?(.*)", lines[i]):
                bq_lines.append(re.match(r"^>\s?(.*)", lines[i]).group(1))
                i += 1
            inner = parse_inline(" ".join(bq_lines))
            out.append(f"<p>{inner}</p>")
            continue
        elif in_blockquote:
            out.append("</blockquote>")
            in_blockquote = False

        # Table
        if "|" in line and line.strip().startswith("|"):
            if not in_table:
                in_table = True
            table_lines = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            out.append(_parse_table(table_lines))
            continue

        # Headings
        h3 = re.match(r"^### (.+)", line)
        if h3:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h3>{parse_inline(h3.group(1))}</h3>")
            i += 1
            continue

        h2 = re.match(r"^## (.+)", line)
        if h2:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h2>{parse_inline(h2.group(1))}</h2>")
            i += 1
            continue

        h1 = re.match(r"^# (.+)", line)
        if h1:
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<h1>{parse_inline(h1.group(1))}</h1>")
            i += 1
            continue

        # Unordered list
        li_match = re.match(r"^- (.+)", line)
        if li_match:
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{parse_inline(li_match.group(1))}</li>")
            i += 1
            continue
        elif in_list and line.strip() == "":
            # Empty line in list = continue list (for multi-line items)
            i += 1
            continue
        elif in_list:
            out.append("</ul>")
            in_list = False

        # Empty line
        if line.strip() == "":
            out.append("")
            i += 1
            continue

        # Regular paragraph
        para_lines = []
        while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].startswith("-") and not lines[i].startswith(">") and not lines[i].startswith("|") and not re.match(r"^---\s*$", lines[i]):
            para_lines.append(lines[i])
            i += 1
        if para_lines:
            out.append(f"<p>{parse_inline(' '.join(para_lines))}</p>")

    if in_list:
        out.append("</ul>")
    if in_blockquote:
        out.append("</blockquote>")

    return "\n".join(out)


def _parse_table(lines: list[str]) -> str:
    """Parse a markdown table into HTML."""
    rows = []
    for line in lines:
        line = line.strip()
        if re.match(r"^\|[-| :]+\|$", line):  # separator row
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        rows.append(cells)

    if not rows:
        return ""

    html = "<table>\n"
    # First row as header
    if rows:
        html += "<thead>\n<tr>\n"
        for cell in rows[0]:
            html += f"<th>{parse_inline(cell)}</th>\n"
        html += "</tr>\n</thead>\n"
    if len(rows) > 1:
        html += "<tbody>\n"
        for row in rows[1:]:
            html += "<tr>\n"
            for cell in row:
                html += f"<td>{parse_inline(cell)}</td>\n"
            html += "</tr>\n"
        html += "</tbody>\n"
    html += "</table>\n"
    return html


def parse_inline(text: str) -> str:
    """Parse inline markdown: bold, italic, links, code, images."""
    # Images: ![alt](url)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', text)
    # Links: [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    # Bold: **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Inline code: `text`
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # Emoji are passed through as-is
    return text


# ── HTML template ────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<title>AI 行业日报</title>
<style>
  :root {
    --bg: #f5f3f0;
    --sidebar-bg: #1a1a2e;
    --sidebar-text: #b0b0c0;
    --sidebar-active: #ffffff;
    --sidebar-hover: #2a2a4e;
    --card-bg: #ffffff;
    --text: #2c2c2c;
    --text-secondary: #6b6b6b;
    --accent: #3b82f6;
    --accent-dim: #2563eb;
    --border: #e5e5e5;
    --tag-bg: #eff6ff;
    --tag-text: #3b82f6;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
      "Hiragino Sans GB", "Microsoft YaHei", "Helvetica Neue", Helvetica, Arial,
      sans-serif;
    background: var(--bg);
    color: var(--text);
    display: flex;
    min-height: 100vh;
  }

  /* ── Sidebar ── */
  nav {
    width: 260px;
    min-width: 260px;
    background: var(--sidebar-bg);
    color: var(--sidebar-text);
    display: flex;
    flex-direction: column;
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    z-index: 10;
    overflow-y: auto;
  }

  .nav-header {
    padding: 28px 24px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }

  .nav-header h1 {
    color: #fff;
    font-size: 18px;
    font-weight: 700;
    letter-spacing: -0.3px;
  }

  .nav-header .subtitle {
    font-size: 12px;
    color: var(--sidebar-text);
    margin-top: 4px;
  }

  .nav-list {
    flex: 1;
    padding: 8px 0;
    list-style: none;
  }

  .nav-list li a {
    display: block;
    padding: 10px 24px;
    color: var(--sidebar-text);
    text-decoration: none;
    font-size: 14px;
    transition: all 0.15s ease;
    border-left: 3px solid transparent;
    cursor: pointer;
  }

  .nav-list li a:hover {
    background: var(--sidebar-hover);
    color: #ddd;
  }

  .nav-list li a.active {
    color: var(--sidebar-active);
    background: rgba(59, 130, 246, 0.15);
    border-left-color: var(--accent);
    font-weight: 600;
  }

  .nav-list li a .date-badge {
    display: inline-block;
    background: rgba(255,255,255,0.1);
    border-radius: 4px;
    padding: 1px 6px;
    font-size: 11px;
    margin-right: 8px;
  }

  .nav-footer {
    padding: 16px 24px;
    border-top: 1px solid rgba(255,255,255,0.08);
    font-size: 11px;
    color: #666;
  }

  /* ── Main content ── */
  main {
    margin-left: 260px;
    flex: 1;
    padding: 32px 40px;
    display: flex;
    justify-content: center;
  }

  .briefing {
    background: var(--card-bg);
    border-radius: 12px;
    padding: 40px 48px;
    max-width: 1000px;
    width: 100%;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    line-height: 1.8;
  }

  .briefing h1 {
    font-size: 26px;
    font-weight: 800;
    margin-bottom: 8px;
    letter-spacing: -0.5px;
  }

  .briefing h2 {
    font-size: 18px;
    font-weight: 700;
    margin-top: 36px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--border);
  }

  .briefing h3 {
    font-size: 15px;
    font-weight: 600;
    margin-top: 24px;
    margin-bottom: 8px;
    color: #444;
  }

  .briefing p {
    margin-bottom: 12px;
  }

  .briefing ul {
    margin: 8px 0 16px 0;
    padding-left: 20px;
  }

  .briefing li {
    margin-bottom: 10px;
    font-size: 15px;
  }

  .briefing li strong {
    color: #1a1a2e;
  }

  .briefing strong {
    font-weight: 600;
  }

  .briefing a {
    color: var(--accent);
    text-decoration: none;
    font-size: 13px;
    border-bottom: 1px solid transparent;
    transition: border-color 0.15s;
  }

  .briefing a:hover {
    border-bottom-color: var(--accent);
  }

  .briefing hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 24px 0;
  }

  .briefing blockquote {
    margin: 16px 0;
    padding: 12px 20px;
    background: #f8f9fa;
    border-left: 4px solid var(--accent);
    border-radius: 0 8px 8px 0;
    font-size: 14px;
    color: #555;
  }

  .briefing code {
    background: #f1f3f5;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
  }

  .briefing table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 14px;
  }

  .briefing th {
    background: #f8f9fa;
    padding: 10px 14px;
    text-align: left;
    font-weight: 600;
    border-bottom: 2px solid var(--border);
  }

  .briefing td {
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
  }

  .briefing tr:hover td {
    background: #fafbfc;
  }

  .empty-state {
    text-align: center;
    padding: 80px 20px;
    color: var(--text-secondary);
  }

  .empty-state .icon {
    font-size: 48px;
    margin-bottom: 16px;
  }

  .empty-state h2 {
    font-size: 20px;
    margin-bottom: 8px;
    color: var(--text);
    border: none;
  }

  /* ── Responsive ── */
  @media (max-width: 768px) {
    nav {
      width: 100%;
      min-width: unset;
      height: auto;
      position: relative;
      flex-direction: row;
      flex-wrap: wrap;
    }
    .nav-list {
      display: flex;
      overflow-x: auto;
    }
    .nav-list li a {
      white-space: nowrap;
      border-left: none;
      border-bottom: 3px solid transparent;
      padding: 10px 16px;
    }
    main {
      margin-left: 0;
      padding: 16px;
    }
    .briefing {
      padding: 24px 20px;
    }
  }
</style>
</head>
<body>

<nav>
  <div class="nav-header">
    <h1>📊 AI 行业日报</h1>
    <div class="subtitle">每日自动更新 · 科研 · 产品 · 融资</div>
  </div>
  <ul class="nav-list" id="navList">
    __NAV_ITEMS__
  </ul>
  <div class="nav-footer">共 __TOTAL__ 期 | 自动生成于 __BUILD_TIME__</div>
</nav>

<main id="main">
  <div class="empty-state">
    <div class="icon">📭</div>
    <h2>选择日期查看日报</h2>
    <p>左侧列表中选择一个日期</p>
  </div>
</main>

<script>
// All briefing data embedded at build time
const BRIEFINGS = __BRIEFINGS_JSON__;

const navList = document.getElementById('navList');
const main = document.getElementById('main');

function renderNav() {
  const dates = Object.keys(BRIEFINGS).sort().reverse();
  navList.innerHTML = dates.map((date, i) => `
    <li>
      <a href="#${date}" class="${i === 0 ? 'active' : ''}"
         onclick="showBriefing('${date}'); return false;">
        <span class="date-badge">${formatDate(date)}</span>
        ${getDayLabel(date)}
      </a>
    </li>
  `).join('');
}

function formatDate(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${mm}/${dd}`;
}

function getDayLabel(dateStr) {
  const d = new Date(dateStr + 'T00:00:00');
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
  return days[d.getDay()];
}

function showBriefing(date) {
  // Update nav active state
  navList.querySelectorAll('a').forEach(a => a.classList.remove('active'));
  const link = navList.querySelector(`a[href="#${date}"]`);
  if (link) link.classList.add('active');

  // Render content
  const html = BRIEFINGS[date];
  if (html) {
    main.innerHTML = `<div class="briefing">${html}</div>`;
    // Scroll to top
    main.scrollTop = 0;
    window.scrollTo(0, 0);
  }
}

// Show latest on load
document.addEventListener('DOMContentLoaded', () => {
  renderNav();
  const dates = Object.keys(BRIEFINGS).sort().reverse();
  if (dates.length > 0) {
    showBriefing(dates[0]);
  }
});

// Handle hash-based navigation
window.addEventListener('hashchange', () => {
  const date = window.location.hash.slice(1);
  if (date && BRIEFINGS[date]) {
    showBriefing(date);
  }
});
</script>

</body>
</html>"""


# ── Build ────────────────────────────────────────────────────────────────────

def build():
    """Main build function."""
    # 先跑校验
    import subprocess
    result = subprocess.run(
        [sys.executable, str(ROOT / "validate.py")],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        print("WARNING: Validation found issues. Run python validate.py for details.")
        print("Continuing with build, but please review.")

    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)

    # Read all markdown files
    md_files = sorted(BRIEFINGS_DIR.glob("*.md"), reverse=True)

    if not md_files:
        print("No briefing files found. Run a daily briefing first.")
        return

    briefings = {}
    for f in md_files:
        date_str = f.stem  # YYYY-MM-DD
        raw = f.read_text(encoding="utf-8")
        html = parse_markdown(raw)
        briefings[date_str] = html

    # Build nav items
    nav_items = []
    for date_str in sorted(briefings.keys(), reverse=True):
        d = datetime.strptime(date_str, "%Y-%m-%d")
        days_cn = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
        day_label = days_cn[d.weekday()] if d.weekday() < 7 else ""
        mmdd = d.strftime("%m/%d")
        nav_items.append(
            f'<li><a href="#{date_str}" onclick="showBriefing(\'{date_str}\');return false">'
            f'<span class="date-badge">{mmdd}</span>{day_label}</a></li>'
        )

    # Build final HTML
    build_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    html_output = HTML_TEMPLATE.replace("__NAV_ITEMS__", "\n".join(nav_items))
    html_output = html_output.replace("__TOTAL__", str(len(briefings)))
    html_output = html_output.replace("__BUILD_TIME__", build_time)
    html_output = html_output.replace("__BRIEFINGS_JSON__", json.dumps(briefings, ensure_ascii=False))

    OUTPUT.write_text(html_output, encoding="utf-8")
    print(f"Built {OUTPUT} with {len(briefings)} briefing(s)")


if __name__ == "__main__":
    build()
