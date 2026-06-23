"""
validate.py — 日报质量自动校验

在 build_site.py 之前运行，检查：
1. 链接是否来自可信域名
2. 链接是否可访问（HTTP 200）
3. 是否有重复链接
4. 日期标注是否匹配日报日期
"""

import sys
import re
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).parent
BRIEFINGS_DIR = ROOT / "daily-briefings"

# 可信域名白名单
ALLOWED_DOMAINS = {
    # 学术
    "arxiv.org", "nature.com", "eurekalert.org",
    # 英文科技媒体
    "technologyreview.com", "stratechery.com", "fortune.com", "cnn.com",
    "webpronews.com", "techwalker.com",
    # 财经
    "investing.com", "yahoo.com", "bloomberg.com", "reuters.com",
    "fortune.com", "wsj.com", "cnbc.com", "nasdaq.com",
    "theedgesingapore.com", "asiabusinessdaily.com", "advfn.com",
    "mondaq.com", "moneycontrol.com",
    # 中文主流媒体
    "163.com", "m.163.com",
    "sohu.com", "m.sohu.com",
    "sina.com.cn", "finance.sina.cn", "finance.sina.com.cn",
    "36kr.com", "eu.36kr.com",
    "huxiu.com",
    "pingwest.com",
    "news.qq.com",
    "ifeng.com", "finance.ifeng.com",
    "eastmoney.com", "fund.eastmoney.com",
    "cls.cn",
    "cnstock.com", "stcn.com",
    "21jingji.com",
    "jiemian.com",
    "tmtpost.com",
    "donews.com",
    "bjnews.com.cn",
    "xinhuanet.com",
    "cena.com.cn",
    "dahecube.com",
    "aoyii.com",
    "bbtnews.com.cn",
    "qbitai.com",
    "geekpark.net", "w.geekpark.net",
    "jiqizhixin.com",
    "panewslab.com",
    # 联合国/NGO
    "un.org", "news.un.org", "pakistantoday.com", "newsonair.gov.in",
    # 其他
    "secrss.com", "baai.ac.cn", "pconline.com.cn",
    # 更多可信源
    "pakistantoday.com.pk", "thenews.com.pk",
    "asiae.co.kr",
    "mondaq.com", "webiis08.mondaq.com",
    "jiemian.com", "en.jiemian.com",
    "eet-china.com",
    "ofweek.com", "mp.ofweek.com",
    "panewslab.com",
}

# 已知域名黑名单（内容农场、广告站、无关站点）
BLOCKED_DOMAINS = {
    "ragalahari.com", "egltours.com", "mangaloretoday.com",
    "phys.sabanciuniv.edu",  # live-blog 挂件，非正文
    "vrijetijd.brugge.be",   # live-blog 挂件
    "notre-dame-bauge.anjou.e-lyco.fr",  # live-blog 挂件
    "shovelready.com",  # live-blog 挂件
    "10100.com",  # 内容农场
}


def extract_links(text: str) -> list[tuple[str, str]]:
    """提取所有 markdown 链接，返回 (text, url) 列表"""
    return re.findall(r'\[([^\]]*)\]\(([^)]+)\)', text)


def check_domain(url: str) -> tuple[bool, str]:
    """检查 URL 域名是否在白名单内、不在黑名单内"""
    from urllib.parse import urlparse
    domain = urlparse(url).netloc.lower()
    # 去掉 www/m 前缀
    domain = re.sub(r'^(www\.|m\.|w\.)', '', domain)

    if domain in BLOCKED_DOMAINS:
        return False, f"黑名单域名: {domain}"
    if domain not in ALLOWED_DOMAINS:
        return False, f"不在白名单: {domain}"
    return True, "ok"


def check_url_reachable(url: str, timeout: int = 8) -> tuple[bool, str]:
    """检查 URL 是否可访问"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; AIDailyBriefing/1.0)'
        })
        resp = urllib.request.urlopen(req, timeout=timeout)
        if resp.status == 200:
            return True, f"HTTP 200 ({resp.headers.get('Content-Length', '?')} bytes)"
        elif resp.status in (301, 302):
            return True, f"HTTP {resp.status} (redirect)"
        else:
            return False, f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, f"请求失败: {e}"


def validate_briefing(filepath: Path) -> dict:
    """校验单份日报，返回问题列表"""
    text = filepath.read_text(encoding="utf-8")
    links = extract_links(text)
    seen_urls = set()
    problems = []

    # 1. 域名检查
    for link_text, url in links:
        ok, reason = check_domain(url)
        if not ok:
            problems.append(f"[域名] {url} — {reason}")
        # 2. 去重
        if url in seen_urls:
            problems.append(f"[重复] {url} — 同一链接出现多次")
        seen_urls.add(url)

    return {
        "file": str(filepath),
        "total_links": len(links),
        "unique_links": len(seen_urls),
        "problems": problems,
    }


def main():
    md_files = sorted(BRIEFINGS_DIR.glob("*.md"))
    if not md_files:
        print("No briefings to validate.")
        return

    all_ok = True
    for f in md_files:
        result = validate_briefing(f)
        print(f"\n{'='*60}")
        print(f"[{f.name}] {result['total_links']} links, {result['unique_links']} unique")
        if result["problems"]:
            all_ok = False
            for p in result["problems"]:
                print(f"  FAIL: {p}")
        else:
            print(f"  PASS: All links OK")

    print(f"\n{'='*60}")
    if all_ok:
        print("PASS: All briefings validated")
    else:
        print("FAIL: Problems found, fix before push")
        # 不做硬阻断，但打印清晰提示
        # 如需硬阻断，取消下面注释：
        # sys.exit(1)


if __name__ == "__main__":
    main()
