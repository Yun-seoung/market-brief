import logging
import os
import ssl

os.environ.setdefault("CURL_CA_BUNDLE", "")
os.environ.setdefault("REQUESTS_CA_BUNDLE", "")
ssl._create_default_https_context = ssl._create_unverified_context

from curl_cffi import requests as cffi_requests
import yfinance as yf

TICKERS = {
    "S&P500":       "^GSPC",
    "NASDAQ":       "^IXIC",
    "DOW":          "^DJI",
    "달러인덱스":    "DX-Y.NYB",
    "미국채10년":    "^TNX",
    "VIX":          "^VIX",
    "KOSPI":        "^KS11",
    "KOSDAQ":       "^KQ11",
    "원달러환율":    "KRW=X",
}

_SESSION = cffi_requests.Session(verify=False, impersonate="chrome")


def get_indicators() -> dict:
    """yfinance로 주요 경제지표 9종 수집. 실패 항목은 None으로 반환."""
    results = {}
    for name, ticker in TICKERS.items():
        try:
            data = yf.Ticker(ticker, session=_SESSION).history(period="2d")
            if data.empty:
                results[name] = {"current": None, "change": None, "change_pct": None}
                continue
            current = float(data["Close"].iloc[-1])
            prev = float(data["Close"].iloc[-2]) if len(data) >= 2 else current
            change = current - prev
            change_pct = (change / prev * 100) if prev else 0.0
            results[name] = {
                "current": round(current, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
            }
        except Exception as e:
            logging.error(f"[fetch_indicators] {name} ({ticker}) 오류: {e}")
            results[name] = {"current": None, "change": None, "change_pct": None}
    return results


if __name__ == "__main__":
    import json
    print(json.dumps(get_indicators(), ensure_ascii=False, indent=2))
