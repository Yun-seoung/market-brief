import logging
import re
import ssl
from datetime import datetime, timedelta, timezone

ssl._create_default_https_context = ssl._create_unverified_context

import feedparser

# (소스명, URL, 국내여부)
RSS_FEEDS = [
    ("국내경제",   "https://news.google.com/rss/search?q=한국+경제+금리+증시&hl=ko&gl=KR&ceid=KR:ko",            True),
    ("국내증시",   "https://news.google.com/rss/search?q=코스피+코스닥+환율&hl=ko&gl=KR&ceid=KR:ko",             True),
    ("글로벌시장", "https://news.google.com/rss/search?q=stock+market+S%26P500+economy&hl=en&gl=US&ceid=US:en",   False),
    ("글로벌거시", "https://news.google.com/rss/search?q=Federal+Reserve+interest+rate+inflation&hl=en&gl=US&ceid=US:en", False),
]

_CUTOFF_HOURS = 36


def _strip_source_suffix(title: str) -> str:
    """Google News 제목 끝의 ' - 출처명' 제거."""
    idx = title.rfind(" - ")
    return title[:idx].strip() if idx > 0 else title


def _translate_ko(text: str) -> str:
    """영어 텍스트를 한국어로 번역. 실패 시 원본 반환."""
    if not text:
        return text
    try:
        import requests
        from deep_translator import GoogleTranslator

        _orig = requests.Session.merge_environment_settings
        def _no_ssl(self, url, proxies, stream, verify, cert):
            s = _orig(self, url, proxies, stream, verify, cert)
            s["verify"] = False
            return s
        requests.Session.merge_environment_settings = _no_ssl
        try:
            result = GoogleTranslator(source="auto", target="ko").translate(text[:500])
        finally:
            requests.Session.merge_environment_settings = _orig

        return result or text
    except Exception:
        return text


_KST = timezone(timedelta(hours=9))


def _pub_dt(entry) -> datetime | None:
    if entry.get("published_parsed"):
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    return None


def get_news(max_items: int = 12) -> list[dict]:
    """Google News RSS에서 경제 뉴스 수집. 국내는 오늘 날짜 기사 우선."""
    cutoff   = datetime.now(tz=timezone.utc) - timedelta(hours=_CUTOFF_HOURS)
    today_kst = datetime.now(_KST).date()
    articles = []

    for source_name, url, is_domestic in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            candidates = []
            for entry in feed.entries:
                title = _strip_source_suffix((entry.get("title") or "").strip())
                link  = entry.get("link") or ""
                if not title or not link:
                    continue
                pub = _pub_dt(entry)
                if pub and pub < cutoff:
                    continue
                raw_summary = entry.get("summary") or entry.get("description") or ""
                summary = re.sub(r"<[^>]+>", "", raw_summary).strip()[:200]
                is_today = pub and pub.astimezone(_KST).date() == today_kst
                candidates.append((is_today, pub or datetime.min.replace(tzinfo=timezone.utc),
                                   title, summary, link))

            # 국내: 오늘 기사 먼저, 글로벌: Google 중요도 순 유지
            if is_domestic:
                candidates.sort(key=lambda x: (not x[0], -x[1].timestamp()))
            else:
                candidates = candidates  # 원래 순서(Google 중요도) 유지

            for _, _, title, summary, link in candidates[:5]:
                if not is_domestic:
                    title   = _translate_ko(title)
                    summary = _translate_ko(summary)
                articles.append({
                    "title":       title,
                    "summary":     summary,
                    "link":        link,
                    "source":      source_name,
                    "is_domestic": is_domestic,
                })

        except Exception as e:
            logging.error(f"[fetch_news] {source_name} RSS 오류: {e}")

    seen = set()
    unique = []
    for a in articles:
        if a["link"] not in seen:
            seen.add(a["link"])
            unique.append(a)

    return unique[:max_items]


if __name__ == "__main__":
    news = get_news()
    print(f"수집된 뉴스: {len(news)}건")
    for n in news:
        tag = "국내" if n["is_domestic"] else "글로벌"
        print(f"  [{tag}] {n['title']}")
