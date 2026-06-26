"""
main.py — Market Brief 일간 브리핑 파이프라인

실행:
    python main.py              # 오늘 브리핑
    python main.py --date 2026-06-25   # 특정 날짜 (지표만 해당날 기준)
    python main.py --skip-email        # 메일 발송 건너뜀 (테스트용)
    python main.py --skip-notion       # 노션 저장 건너뜀 (테스트용)
"""

import argparse
import logging
import os
import ssl
import sys
from datetime import datetime
from pathlib import Path

# Windows 기업 네트워크 SSL 인증서 문제 우회
os.environ.setdefault("CURL_CA_BUNDLE", "")
os.environ.setdefault("REQUESTS_CA_BUNDLE", "")
ssl._create_default_https_context = ssl._create_unverified_context

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# basicConfig 이후 모든 root handler에 fonttools 필터 강제 적용
class _NoFonttoolsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not record.name.lower().startswith("fonttools")

_ft_filter = _NoFonttoolsFilter()
for _h in logging.getLogger().handlers:
    _h.addFilter(_ft_filter)


def _setup_log_file(date_str: str):
    Path("outputs").mkdir(exist_ok=True)
    fh = logging.FileHandler(f"outputs/{date_str}.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(fh)


def _build_highlights(indicators: dict, news: list, events: list) -> list[str]:
    """국내 주식시장 이슈 3개 + 미국 주식시장 이슈 3개."""
    domestic = [n for n in news if n.get("is_domestic")]
    global_  = [n for n in news if not n.get("is_domestic")]

    highlights = []

    for n in domestic[:3]:
        highlights.append(f"[국내] {n['title']}")
    while len([h for h in highlights if h.startswith("[국내]")]) < 3:
        highlights.append("[국내] 국내 경제 뉴스 수집 없음")

    for n in global_[:3]:
        highlights.append(f"[미국] {n['title']}")
    while len([h for h in highlights if h.startswith("[미국]")]) < 3:
        highlights.append("[미국] 글로벌 시장 뉴스 수집 없음")

    return highlights


def run(date_str: str, skip_email: bool = False, skip_notion: bool = False, update_mode: bool = False):
    logging.info(f"{'='*50}")
    logging.info(f"Market Brief 생성 시작: {date_str}")
    logging.info(f"{'='*50}")

    _setup_log_file(date_str)
    status = {}

    # ── 1. 데이터 수집 ─────────────────────────────────────
    logging.info("[1/5] 경제지표 수집 중...")
    try:
        from tools.fetch_indicators import get_indicators
        indicators = get_indicators()
        status["indicators"] = "ok"
        logging.info(f"       → {len(indicators)}종 수집 완료")
    except Exception as e:
        logging.error(f"       경제지표 수집 실패: {e}")
        indicators = {}
        status["indicators"] = "failed"

    logging.info("[2/5] 뉴스 수집 중...")
    try:
        from tools.fetch_news import get_news
        news = get_news()
        status["news"] = "ok"
        logging.info(f"       → {len(news)}건 수집 완료")
    except Exception as e:
        logging.error(f"       뉴스 수집 실패: {e}")
        news = []
        status["news"] = "failed"

    logging.info("[3/5] 이벤트 캘린더 수집 중...")
    try:
        from tools.fetch_events import get_events
        events = get_events()
        status["events"] = "ok"
        logging.info(f"       → {len(events)}건 수집 완료")
    except Exception as e:
        logging.error(f"       이벤트 수집 실패: {e}")
        events = []
        status["events"] = "failed"

    # ── 브리핑 데이터 구성 ────────────────────────────────
    highlights = _build_highlights(indicators, news, events)
    briefing_data = {
        "date":        date_str,
        "indicators":  indicators,
        "news":        news,
        "events":      events,
        "highlights":  highlights,
        "total_count": len(news) + len(events),
    }

    # ── 2. PDF 생성 ────────────────────────────────────────
    logging.info("[4/5] PDF 생성 중...")
    pdf_path = ""
    try:
        from tools.generate_pdf import create_pdf
        pdf_path = create_pdf(briefing_data)
        status["pdf"] = "ok"
        logging.info(f"       → 저장: {pdf_path}")
    except Exception as e:
        logging.error(f"       PDF 생성 실패: {e}")
        status["pdf"] = "failed"

    # ── 3. 메일 발송 ───────────────────────────────────────
    if skip_email:
        logging.info("[5/5] 메일 발송 건너뜀 (--skip-email)")
        status["email"] = "skipped"
    else:
        logging.info("[5/5] 메일 발송 중...")
        try:
            from tools.send_email import send_briefing_email
            success = send_briefing_email(briefing_data, pdf_path)
            status["email"] = "ok" if success else "failed"
        except Exception as e:
            logging.error(f"       메일 발송 실패: {e}")
            status["email"] = "failed"

    # ── 4. 노션 저장 / 업데이트 ────────────────────────────
    if skip_notion:
        logging.info("[+] 노션 저장 건너뜀 (--skip-notion)")
        status["notion"] = "skipped"
    elif update_mode:
        logging.info("[+] 노션 업데이트 중 (--update)...")
        try:
            from tools.save_notion import update_notion
            success = update_notion(briefing_data)
            status["notion"] = "ok" if success else "failed"
        except Exception as e:
            logging.error(f"       노션 업데이트 실패: {e}")
            status["notion"] = "failed"
    else:
        logging.info("[+] 노션 저장 중...")
        try:
            from tools.save_notion import save_to_notion
            success = save_to_notion(briefing_data)
            status["notion"] = "ok" if success else "failed"
        except Exception as e:
            logging.error(f"       노션 저장 실패: {e}")
            status["notion"] = "failed"

    # ── 최종 결과 출력 ─────────────────────────────────────
    logging.info(f"{'='*50}")
    logging.info("완료 요약:")
    icons = {"ok": "[OK]", "failed": "[FAIL]", "skipped": "[-]"}
    for step, result in status.items():
        logging.info(f"  {icons.get(result, '?')} {step}: {result}")
    logging.info(f"{'='*50}")

    all_ok = all(v in ("ok", "skipped") for v in status.values())
    return 0 if all_ok else 1


def main():
    parser = argparse.ArgumentParser(description="Market Brief 일간 브리핑 생성")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"),
                        help="브리핑 날짜 (기본: 오늘, 형식: YYYY-MM-DD)")
    parser.add_argument("--skip-email", action="store_true", help="메일 발송 건너뜀")
    parser.add_argument("--skip-notion", action="store_true", help="노션 저장 건너뜀")
    parser.add_argument("--update", action="store_true", help="기존 페이지 업데이트 (새 페이지 생성 안함)")
    args = parser.parse_args()

    exit_code = run(
        date_str=args.date,
        skip_email=args.skip_email,
        skip_notion=args.skip_notion,
        update_mode=args.update,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
