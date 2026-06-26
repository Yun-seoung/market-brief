import logging
import re
import ssl
import warnings
from datetime import datetime

import requests
import urllib3
from bs4 import BeautifulSoup

ssl._create_default_https_context = ssl._create_unverified_context
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# 관심 통화 (고영향 이벤트 필터링)
_CURRENCIES_OF_INTEREST = {"USD", "KRW", "CNY", "EUR", "GBP", "JPY"}
_HIGH_IMPACT_ONLY = False  # True로 바꾸면 high impact만


def get_events() -> list[dict]:
    """ForexFactory 캘린더에서 오늘 예정된 주요 경제 이벤트 수집.
    각 항목: time, currency, impact, event, forecast, previous."""
    try:
        return _scrape_forexfactory()
    except Exception as e:
        logging.error(f"[fetch_events] ForexFactory 스크래핑 실패: {e}")
        return []


def _scrape_forexfactory() -> list[dict]:
    url = "https://www.forexfactory.com/calendar"
    resp = requests.get(url, headers=_HEADERS, timeout=15, verify=False)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table", class_=re.compile(r"calendar"))
    if not table:
        logging.warning("[fetch_events] 캘린더 테이블을 찾을 수 없습니다.")
        return []

    events = []
    current_time = ""

    for row in table.find_all("tr", class_=re.compile(r"calendar__row")):
        try:
            # 시간 셀 (비어있으면 이전 행 시간 재사용)
            time_cell = row.find("td", class_=re.compile(r"calendar__time"))
            if time_cell and time_cell.get_text(strip=True):
                current_time = time_cell.get_text(strip=True)

            currency_cell = row.find("td", class_=re.compile(r"calendar__currency"))
            currency = currency_cell.get_text(strip=True) if currency_cell else ""

            if currency not in _CURRENCIES_OF_INTEREST:
                continue

            impact_cell = row.find("td", class_=re.compile(r"calendar__impact"))
            impact = ""
            if impact_cell:
                span = impact_cell.find("span")
                if span:
                    classes = " ".join(span.get("class", []))
                    if "high" in classes:
                        impact = "high"
                    elif "medium" in classes:
                        impact = "medium"
                    else:
                        impact = "low"

            if _HIGH_IMPACT_ONLY and impact != "high":
                continue

            event_cell = row.find("td", class_=re.compile(r"calendar__event"))
            event_name = event_cell.get_text(strip=True) if event_cell else ""
            if not event_name:
                continue

            forecast_cell = row.find("td", class_=re.compile(r"calendar__forecast"))
            forecast = forecast_cell.get_text(strip=True) if forecast_cell else ""

            previous_cell = row.find("td", class_=re.compile(r"calendar__previous"))
            previous = previous_cell.get_text(strip=True) if previous_cell else ""

            events.append({
                "time": current_time,
                "currency": currency,
                "impact": impact,
                "event": event_name,
                "forecast": forecast,
                "previous": previous,
            })
        except Exception as e:
            logging.debug(f"[fetch_events] 행 파싱 오류: {e}")
            continue

    return events


if __name__ == "__main__":
    import json
    events = get_events()
    print(f"수집된 이벤트: {len(events)}건")
    for ev in events:
        print(f"  {ev['time']:8s} [{ev['currency']}] ({ev['impact']:6s}) {ev['event']}")
