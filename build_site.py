"""
AI Daily Briefing — Static Site Builder v2

Interactive HTML with collapsible sections, floating ToC, and article images.
Fetches og:image from article URLs at build time with JSON cache.
"""

import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).parent
BRIEFINGS_DIR = ROOT / "daily-briefings"
OUTPUT = ROOT / "index.html"
CACHE_FILE = ROOT / ".image_cache.json"

# ── Image fetcher ──────────────────────────────────────────────────────────────

def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {}

def save_cache(cache: dict):
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')

def fetch_og_image(url: str, cache: dict) -> str | None:
    """Extract og:image from a URL. Uses cache to avoid repeated fetches."""
    if url in cache:
        return cache[url]  # None means tried and failed

    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; AIDailyBriefing/2.0)'
        })
        resp = urllib.request.urlopen(req, timeout=6)
        # Read first 128KB, enough for head section
        html = resp.read(128 * 1024).decode('utf-8', errors='replace')

        # Try og:image
        m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html, re.I)
        if m:
            img = m.group(1)
            cache[url] = img
            return img
        # Try twitter:image
        m = re.search(r'<meta\s+name="twitter:image"\s+content="([^"]+)"', html, re.I)
        if m:
            img = m.group(1)
            cache[url] = img
            return img
        # Try first <img> with reasonable src
        m = re.search(r'<img[^>]+src="(https?://[^"]+\.(?:png|jpg|jpeg|webp))"', html, re.I)
        if m:
            img = m.group(1)
            cache[url] = img
            return img
    except Exception:
        pass

    cache[url] = None  # Mark as tried
    return None

# ── Markdown parser ────────────────────────────────────────────────────────────

def parse_markdown(text: str) -> str:
    """Convert markdown to HTML."""
    lines = text.split("\n")
    out = []
    in_list = False
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
            i += 1
            continue

        # Blockquote
        bq_match = re.match(r"^>\s?(.*)", line)
        if bq_match:
            if not in_blockquote:
                out.append('<blockquote>')
                in_blockquote = True
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
            table_lines = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            out.append(_parse_table(table_lines))
            continue

        # Headings -> add id for ToC anchor
        h3 = re.match(r"^### (.+)", line)
        if h3:
            if in_list:
                out.append("</ul>"); in_list = False
            anchor = slugify(h3.group(1))
            out.append(f'<h3 id="{anchor}">{parse_inline(h3.group(1))}</h3>')
            i += 1; continue

        h2 = re.match(r"^## (.+)", line)
        if h2:
            if in_list:
                out.append("</ul>"); in_list = False
            anchor = slugify(h2.group(1))
            out.append(f'<h2 id="{anchor}">{parse_inline(h2.group(1))}</h2>')
            i += 1; continue

        h1 = re.match(r"^# (.+)", line)
        if h1:
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f'<h1>{parse_inline(h1.group(1))}</h1>')
            i += 1; continue

        # List item
        li_match = re.match(r"^- (.+)", line)
        if li_match:
            if not in_list:
                out.append('<ul>'); in_list = True
            out.append(f"<li>{parse_inline(li_match.group(1))}</li>")
            i += 1; continue
        elif in_list and line.strip() == "":
            i += 1; continue
        elif in_list:
            out.append("</ul>"); in_list = False

        # Empty
        if line.strip() == "":
            out.append("")
            i += 1; continue

        # Paragraph
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
    rows = []
    for line in lines:
        line = line.strip()
        if re.match(r"^\|[-| :]+\|$", line):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        rows.append(cells)
    if not rows:
        return ""
    html = "<table>\n"
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
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text

def slugify(text: str) -> str:
    """Generate an anchor ID from heading text."""
    # Remove emoji and special chars, keep Chinese/English/digits
    cleaned = re.sub(r'[^\w一-鿿\s-]', '', text)
    return re.sub(r'\s+', '-', cleaned.strip()).lower()[:40]

def extract_article_links(html: str) -> list[str]:
    """Extract all external article URLs from parsed HTML (not internal anchors)."""
    urls = re.findall(r'href="(https?://[^"]+)"', html)
    # Deduplicate and filter out common non-article domains
    seen = set()
    result = []
    skip = {'github.com', 'leoljq.github.io'}
    for u in urls:
        if u not in seen:
            seen.add(u)
            if not any(s in u for s in skip):
                result.append(u)
    return result

# ── HTML template ──────────────────────────────────────────────────────────────

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
    --bg: #f7f6f3;
    --sidebar-bg: #111827;
    --sidebar-text: #9ca3af;
    --sidebar-active: #ffffff;
    --sidebar-hover: #1f2937;
    --card-bg: #ffffff;
    --text: #1f2937;
    --text-secondary: #6b7280;
    --accent: #2563eb;
    --accent-light: #eff6ff;
    --border: #e5e7eb;
    --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    --shadow-hover: 0 4px 12px rgba(0,0,0,0.08);
    --radius: 10px;
    --transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
      "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    background: var(--bg);
    color: var(--text);
    display: flex;
    min-height: 100vh;
    font-size: 15px;
    line-height: 1.7;
  }

  /* ── Sidebar ── */
  nav {
    width: 240px; min-width: 240px;
    background: var(--sidebar-bg);
    color: var(--sidebar-text);
    display: flex; flex-direction: column;
    position: fixed; top: 0; left: 0; bottom: 0; z-index: 100;
    overflow-y: auto;
  }
  .nav-header {
    padding: 24px 20px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
  }
  .nav-header h1 { color: #fff; font-size: 16px; font-weight: 700; }
  .nav-header .subtitle { font-size: 11px; color: var(--sidebar-text); margin-top: 2px; }
  .nav-list { flex: 1; padding: 6px 0; list-style: none; }
  .nav-list li a {
    display: block; padding: 9px 20px; color: var(--sidebar-text);
    text-decoration: none; font-size: 13px;
    transition: all var(--transition);
    border-left: 3px solid transparent; cursor: pointer;
  }
  .nav-list li a:hover { background: var(--sidebar-hover); color: #ddd; }
  .nav-list li a.active {
    color: var(--sidebar-active);
    background: rgba(37, 99, 235, 0.18);
    border-left-color: var(--accent); font-weight: 600;
  }
  .nav-list li a .date-badge {
    display: inline-block; background: rgba(255,255,255,0.08);
    border-radius: 4px; padding: 1px 6px; font-size: 11px; margin-right: 6px;
  }
  .nav-footer {
    padding: 14px 20px; border-top: 1px solid rgba(255,255,255,0.06);
    font-size: 11px; color: #555;
  }

  /* ── Floating ToC ── */
  .toc {
    position: fixed; top: 32px; right: 24px; z-index: 90;
    width: 180px; font-size: 12px; opacity: 0; transform: translateX(10px);
    transition: opacity var(--transition), transform var(--transition);
    pointer-events: none;
  }
  .toc.visible { opacity: 1; transform: translateX(0); pointer-events: auto; }
  .toc-title { font-weight: 600; color: var(--text); margin-bottom: 8px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
  .toc a {
    display: block; padding: 3px 0; color: var(--text-secondary);
    text-decoration: none; border-left: 2px solid transparent;
    padding-left: 8px; transition: all var(--transition);
  }
  .toc a:hover, .toc a.active { color: var(--accent); border-left-color: var(--accent); }

  /* ── Main ── */
  main {
    margin-left: 240px; flex: 1; padding: 28px 40px;
    display: flex; justify-content: center; min-height: 100vh;
  }
  .briefing {
    background: transparent;
    width: 100%; max-width: 840px;
  }

  /* ── Header card ── */
  .briefing h1 {
    font-size: 24px; font-weight: 800; letter-spacing: -0.5px;
    background: var(--card-bg); border-radius: var(--radius);
    padding: 24px 32px; box-shadow: var(--shadow); margin-bottom: 20px;
  }

  /* ── Section accordions ── */
  .section {
    background: var(--card-bg); border-radius: var(--radius);
    box-shadow: var(--shadow); margin-bottom: 14px;
    overflow: hidden; transition: box-shadow var(--transition);
  }
  .section:hover { box-shadow: var(--shadow-hover); }

  .section-header {
    display: flex; align-items: center; gap: 10px;
    padding: 14px 24px; cursor: pointer; user-select: none;
    transition: background var(--transition);
    border-bottom: 1px solid transparent;
  }
  .section-header:hover { background: #fafbfc; }
  .section.open .section-header { border-bottom-color: var(--border); }

  .section-header h2, .section-header h3 {
    flex: 1; font-size: 15px; font-weight: 700; margin: 0; padding: 0; border: none;
    color: var(--text);
  }
  .section-arrow {
    width: 20px; height: 20px; display: flex; align-items: center; justify-content: center;
    transition: transform var(--transition); font-size: 10px; color: var(--text-secondary);
  }
  .section.open .section-arrow { transform: rotate(90deg); }

  .section-body {
    max-height: 0; overflow: hidden;
    transition: max-height 0.4s cubic-bezier(0.4, 0, 0.2, 1), padding 0.3s;
  }
  .section.open .section-body {
    max-height: 20000px; padding: 16px 24px 20px;
  }

  /* ── Article cards (inside curated) ── */
  .article-card {
    display: flex; gap: 14px; padding: 12px 0;
    border-bottom: 1px solid var(--border);
    align-items: flex-start;
  }
  .article-card:last-child { border-bottom: none; }
  .article-card .card-img {
    width: 80px; height: 56px; border-radius: 6px;
    object-fit: cover; flex-shrink: 0; background: #f3f4f6;
  }
  .article-card .card-body { flex: 1; min-width: 0; }
  .article-card .card-body strong { display: block; margin-bottom: 2px; font-size: 14px; }
  .article-card .card-body p { font-size: 13px; color: var(--text-secondary); margin: 2px 0 0; }

  /* ── Standard list items style ── */
  .section-body li { margin-bottom: 10px; font-size: 14px; line-height: 1.75; }
  .section-body li strong { color: var(--text); }
  .section-body a { color: var(--accent); text-decoration: none; font-size: 12px; }
  .section-body a:hover { text-decoration: underline; }

  .section-body p { margin-bottom: 10px; font-size: 14px; }
  .section-body h2 { font-size: 16px; font-weight: 700; margin: 20px 0 10px; padding-bottom: 6px; border-bottom: 1px solid var(--border); }
  .section-body h3 { font-size: 14px; font-weight: 600; margin: 16px 0 8px; color: #444; }

  blockquote {
    margin: 12px 0; padding: 10px 16px;
    background: #f9fafb; border-left: 3px solid var(--accent);
    border-radius: 0 6px 6px 0; font-size: 13px; color: #666;
  }
  table { width: 100%; border-collapse: collapse; margin: 12px 0; font-size: 13px; }
  th { background: #f9fafb; padding: 8px 12px; text-align: left; font-weight: 600; border-bottom: 2px solid var(--border); }
  td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
  hr { border: none; border-top: 1px solid var(--border); margin: 16px 0; }
  code { background: #f1f5f9; padding: 1px 5px; border-radius: 4px; font-size: 12px; }

  /* ── Floating image preview ── */
  .img-preview {
    position: fixed; bottom: 20px; right: 220px; z-index: 200;
    max-width: 320px; max-height: 220px; border-radius: 8px;
    box-shadow: 0 8px 30px rgba(0,0,0,0.2); display: none;
    object-fit: cover; pointer-events: none;
  }

  /* ── Responsive ── */
  @media (max-width: 1200px) { .toc { display: none; } }
  @media (max-width: 768px) {
    nav { width: 100%; min-width: unset; height: auto; position: relative; flex-direction: row; flex-wrap: wrap; }
    .nav-list { display: flex; overflow-x: auto; }
    .nav-list li a { white-space: nowrap; border-left: none; border-bottom: 3px solid transparent; padding: 8px 14px; }
    main { margin-left: 0; padding: 14px; }
    .section-header { padding: 12px 16px; }
    .section.open .section-body { padding: 12px 16px; }
    .article-card { flex-direction: column; }
    .article-card .card-img { width: 100%; height: 120px; }
  }
</style>
</head>
<body>

<nav>
  <div class="nav-header">
    <h1>AI 行业日报</h1>
    <div class="subtitle">科研 · 产品 · 融资 · 精选</div>
  </div>
  <ul class="nav-list" id="navList">__NAV_ITEMS__</ul>
  <div class="nav-footer">共 __TOTAL__ 期</div>
</nav>

<div class="toc" id="toc">
  <div class="toc-title">本页目录</div>
  <div id="tocLinks"></div>
</div>

<main id="main">
  <div style="text-align:center;padding:80px 20px;color:var(--text-secondary);">
    <p>选择左侧日期查看日报</p>
  </div>
</main>

<img class="img-preview" id="imgPreview" alt="">

<script>
const BRIEFINGS = __BRIEFINGS_JSON__;
const IMAGES = __IMAGES_JSON__;

const navList = document.getElementById('navList');
const main = document.getElementById('main');
const toc = document.getElementById('toc');
const tocLinks = document.getElementById('tocLinks');
const imgPreview = document.getElementById('imgPreview');

// ── Nav ──
function renderNav() {
  const dates = Object.keys(BRIEFINGS).sort().reverse();
  navList.innerHTML = dates.map((d, i) => {
    const dt = new Date(d + 'T00:00:00');
    const mmdd = String(dt.getMonth()+1).padStart(2,'0') + '/' + String(dt.getDate()).padStart(2,'0');
    const days = ['周日','周一','周二','周三','周四','周五','周六'];
    return `<li><a href="#${d}" class="${i===0?'active':''}" onclick="showBriefing('${d}');return false">
      <span class="date-badge">${mmdd}</span>${days[dt.getDay()]}</a></li>`;
  }).join('');
}

// ── Build ToC ──
function buildToc() {
  const headings = main.querySelectorAll('h2[id], h3[id]');
  tocLinks.innerHTML = Array.from(headings).map(h => {
    const tag = h.tagName.toLowerCase();
    return `<a href="#${h.id}" style="padding-left:${tag==='h3'?'16px':'8px'}">${h.textContent}</a>`;
  }).join('');

  // Highlight on scroll
  const links = tocLinks.querySelectorAll('a');
  const observer = new IntersectionObserver(entries => {
    entries.forEach(e => {
      const id = e.target.id;
      const link = tocLinks.querySelector(`a[href="#${id}"]`);
      if (e.isIntersecting && link) {
        links.forEach(l => l.classList.remove('active'));
        link.classList.add('active');
      }
    });
  }, { rootMargin: '-80px 0px -70% 0px' });
  headings.forEach(h => observer.observe(h));
}

// ── Toggle sections ──
function initSections() {
  main.querySelectorAll('.section-header').forEach(header => {
    header.addEventListener('click', () => {
      const section = header.parentElement;
      const wasOpen = section.classList.contains('open');
      section.classList.toggle('open');
      // Scroll to section if opening
      if (!wasOpen && section.querySelector('h2')) {
        setTimeout(() => section.querySelector('h2').scrollIntoView({behavior:'smooth',block:'start'}), 100);
      }
    });
  });
  // Open first two sections by default
  const sections = main.querySelectorAll('.section');
  sections.forEach((s, i) => { if (i < 2) s.classList.add('open'); });
}

// ── Image hover preview ──
function initImagePreviews() {
  main.querySelectorAll('a[href]').forEach(a => {
    const url = a.getAttribute('href');
    if (!url || !url.startsWith('http')) return;
    // Check if this URL has an associated image
    const img = IMAGES[url];
    if (!img) return;
    a.addEventListener('mouseenter', () => {
      imgPreview.src = img;
      imgPreview.style.display = 'block';
    });
    a.addEventListener('mouseleave', () => {
      imgPreview.style.display = 'none';
    });
  });
}

// ── Render briefing ──
function wrapSections(html) {
  // Wrap h2 + following content into <div class="section">
  // Simple approach: split by <h2, wrap each
  let result = html;
  // Match h2 with optional id, followed by content until next h2 or end
  result = result.replace(/(<h2[^>]*>.*?<\/h2>)((?:(?!<h2[^>]*>)[\\s\\S])*?)(?=<h2[^>]*>|$)/gi, (match, h2, body) => {
    const isOpen = body.includes('id="') && (body.includes('科研学术') || body.includes('产品应用'));
    return `<div class="section"><div class="section-header">${h2}<span class="section-arrow">▶</span></div><div class="section-body">${body}</div></div>`;
  });
  return result;
}

function showBriefing(date) {
  navList.querySelectorAll('a').forEach(a => a.classList.remove('active'));
  const link = navList.querySelector(`a[href="#${date}"]`);
  if (link) link.classList.add('active');

  let html = BRIEFINGS[date];
  if (!html) {
    main.innerHTML = '<div style="text-align:center;padding:80px">未找到该日期日报</div>';
    return;
  }

  // Inject images into article links
  html = injectImages(html);

  // Wrap sections
  html = wrapSections(html);

  main.innerHTML = `<div class="briefing">${html}</div>`;

  initSections();
  initImagePreviews();
  buildToc();
  main.scrollTop = 0;
  window.scrollTo(0, 0);

  // Show ToC after a brief delay
  setTimeout(() => toc.classList.add('visible'), 400);
}

function injectImages(html) {
  // Find <li> items with <a> links and add thumbnail if image exists
  const div = document.createElement('div');
  div.innerHTML = html;

  div.querySelectorAll('li').forEach(li => {
    const a = li.querySelector('a[href]');
    if (!a) return;
    const url = a.getAttribute('href');
    const img = IMAGES[url];
    if (!img) return;

    // Check if this is a long-form article (has <strong>)
    const hasStrong = li.querySelector('strong');
    if (hasStrong) {
      // Wrap in card layout
      const content = li.innerHTML;
      li.innerHTML = `<div class="article-card">
        <img class="card-img" src="${img}" loading="lazy" onerror="this.style.display='none'">
        <div class="card-body">${content}</div>
      </div>`;
      li.style.listStyle = 'none';
    }
  });

  return div.innerHTML;
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  renderNav();
  const dates = Object.keys(BRIEFINGS).sort().reverse();
  if (dates.length > 0) showBriefing(dates[0]);

  // Hide ToC when scrolling past the briefing
  let tocTimer;
  window.addEventListener('scroll', () => {
    clearTimeout(tocTimer);
    toc.classList.add('visible');
    tocTimer = setTimeout(() => {
      if (window.scrollY < 200) toc.classList.remove('visible');
    }, 3000);
  });
});

window.addEventListener('hashchange', () => {
  const date = window.location.hash.slice(1);
  if (date && BRIEFINGS[date]) showBriefing(date);
});
</script>
</body>
</html>"""

# ── Build ────────────────────────────────────────────────────────────────────

def build():
    import subprocess
    # Pre-validation
    result = subprocess.run(
        [sys.executable, str(ROOT / "validate.py")],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stdout)
        print("WARNING: Validation found issues. Continuing, but review recommended.")

    BRIEFINGS_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(BRIEFINGS_DIR.glob("*.md"), reverse=True)
    if not md_files:
        print("No briefing files found.")
        return

    # Load image cache
    image_cache = load_cache()
    global_image_map = {}

    briefings = {}
    for f in md_files:
        date_str = f.stem
        raw = f.read_text(encoding="utf-8")
        html = parse_markdown(raw)

        # Fetch og:images for this briefing's articles
        urls = extract_article_links(html)
        for url in urls:
            if url not in global_image_map:
                img = fetch_og_image(url, image_cache)
                if img:
                    global_image_map[url] = img

        briefings[date_str] = html

    # Save image cache
    save_cache(image_cache)

    # Build nav
    nav_items = []
    for date_str in sorted(briefings.keys(), reverse=True):
        d = datetime.strptime(date_str, "%Y-%m-%d")
        days_cn = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
        day_label = days_cn[d.weekday()]
        mmdd = d.strftime("%m/%d")
        nav_items.append(
            f'<li><a href="#{date_str}" onclick="showBriefing(\'{date_str}\');return false">'
            f'<span class="date-badge">{mmdd}</span>{day_label}</a></li>'
        )

    # Build HTML
    build_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    html_output = HTML_TEMPLATE
    html_output = html_output.replace("__NAV_ITEMS__", "\n".join(nav_items))
    html_output = html_output.replace("__TOTAL__", str(len(briefings)))
    html_output = html_output.replace("__BRIEFINGS_JSON__", json.dumps(briefings, ensure_ascii=False))
    html_output = html_output.replace("__IMAGES_JSON__", json.dumps(global_image_map, ensure_ascii=False))

    OUTPUT.write_text(html_output, encoding="utf-8")
    img_count = len([v for v in global_image_map.values() if v])
    print(f"Built {OUTPUT} with {len(briefings)} briefing(s), {img_count} article image(s)")

if __name__ == "__main__":
    build()
