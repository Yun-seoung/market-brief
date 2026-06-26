import logging
import os
import ssl
from datetime import datetime

import httpx
from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError

ssl._create_default_https_context = ssl._create_unverified_context
load_dotenv()

_INDICATOR_ORDER = [
    "S&P500", "NASDAQ", "DOW", "달러인덱스", "미국채10년", "VIX",
    "KOSPI", "KOSDAQ", "원달러환율",
]


def _rt(text: str) -> list:
    return [{"type": "text", "text": {"content": str(text)}}]


def _rt_link(text: str, url: str) -> list:
    if url:
        return [{"type": "text", "text": {"content": str(text), "link": {"url": url}}}]
    return _rt(text)


def _h1(text: str) -> dict:
    return {"object": "block", "type": "heading_1",
            "heading_1": {"rich_text": _rt(text)}}


def _h2(text: str) -> dict:
    return {"object": "block", "type": "heading_2",
            "heading_2": {"rich_text": _rt(text)}}


def _numbered(text: str) -> dict:
    return {"object": "block", "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": _rt(text)}}


def _bullet(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": _rt(text)}}


def _divider() -> dict:
    return {"object": "block", "type": "divider", "divider": {}}


def _paragraph(text: str) -> dict:
    return {"object": "block", "type": "paragraph",
            "paragraph": {"rich_text": _rt(text)}}


def _table(headers: list, rows: list) -> dict:
    def row_block(cells: list) -> dict:
        return {"type": "table_row", "table_row": {"cells": cells}}

    header_row = row_block([_rt(h) for h in headers])
    data_rows  = [row_block(cells) for cells in rows]

    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": len(headers),
            "has_column_header": True,
            "has_row_header": False,
            "children": [header_row] + data_rows,
        },
    }


def _news_table(articles: list) -> dict:
    rows = []
    for n in articles[:6]:
        title   = n.get("title", "")[:100]
        summary = n.get("summary", "")[:150]
        source  = n.get("source", "")
        link    = n.get("link", "")
        rows.append([_rt(title), _rt(summary), _rt_link(source, link)])
    if not rows:
        rows = [[_rt("수집된 뉴스 없음"), _rt(""), _rt("")]]
    return _table(["항목", "내용", "출처"], rows)


def _indicator_table(indicators: dict) -> dict:
    rows = []
    for name in _INDICATOR_ORDER:
        data = indicators.get(name, {})
        current    = data.get("current")
        change     = data.get("change")
        change_pct = data.get("change_pct")
        if current is not None:
            sign   = "+" if (change or 0) >= 0 else ""
            cur_str = f"{current:,.2f}"
            pct_str = f"{sign}{change_pct:.2f}%" if change_pct is not None else "-"
        else:
            cur_str = "-"
            pct_str = "-"
        rows.append([_rt(name), _rt(cur_str), _rt(pct_str)])
    return _table(["지표", "현재값", "전일대비"], rows)


def _make_blocks(briefing_data: dict) -> list:
    highlights = briefing_data.get("highlights", [])
    news       = briefing_data.get("news", [])
    events     = briefing_data.get("events", [])
    indicators = briefing_data.get("indicators", {})

    domestic = [n for n in news if n.get("is_domestic")]
    global_  = [n for n in news if not n.get("is_domestic")]

    blocks = []

    # H1: 핵심 요약
    blocks.append(_h1("📊 오늘의 핵심 요약"))
    for h in highlights[:6]:
        blocks.append(_numbered(h))
    blocks.append(_divider())

    # H2: 국내 경제
    blocks.append(_h2("🇰🇷 국내 경제"))
    blocks.append(_news_table(domestic))

    # H2: 글로벌 시장
    blocks.append(_h2("🌍 글로벌 시장"))
    blocks.append(_news_table(global_))

    # H2: 경제 지표
    blocks.append(_h2("📈 경제 지표"))
    blocks.append(_indicator_table(indicators))

    # H2: 오늘 예정 이벤트
    blocks.append(_h2("📅 오늘 예정 이벤트"))
    if events:
        for ev in events[:10]:
            text = f"[{ev.get('time', '')}] [{ev.get('currency', '')}] {ev.get('event', '')}"
            blocks.append(_bullet(text))
    else:
        blocks.append(_bullet("예정 이벤트 없음"))

    blocks.append(_divider())
    blocks.append(_paragraph(f"수집 시각: {datetime.now().strftime('%H:%M')} KST"))

    return blocks


def _prop_text(content: str) -> dict:
    return {"rich_text": [{"type": "text", "text": {"content": content[:2000]}}]}


def _indicator_summary_rich(indicators: dict) -> list:
    """지표요약 DB 컬럼용 rich_text — 상승 빨강, 하락 파랑 (한국 증시 관례)."""
    order = ["S&P500", "NASDAQ", "원달러환율", "KOSPI", "VIX"]
    rt_list = []
    for name in order:
        data = indicators.get(name, {})
        cur = data.get("current")
        if cur is None:
            continue
        pct    = data.get("change_pct")
        change = data.get("change") or 0
        sign   = "+" if change >= 0 else ""
        pct_str = f"{sign}{pct:.2f}%" if pct is not None else ""

        if rt_list:
            rt_list.append({"type": "text", "text": {"content": "\n\n"}})

        color = "red" if change > 0 else ("blue" if change < 0 else "default")
        rt_list.append({
            "type": "text",
            "text": {"content": f"{name} {cur:,.0f}({pct_str})"},
            "annotations": {"color": color},
        })
    return rt_list or [{"type": "text", "text": {"content": "-"}}]


def _events_summary(events: list) -> str:
    high = [ev for ev in events if ev.get("impact") in ("high", "medium")][:3]
    targets = high or events[:3]
    lines = [f"[{ev.get('currency','')}] {ev.get('event','')}" for ev in targets]
    return ", ".join(lines) or "예정 이벤트 없음"


def _briefing_summary(highlights: list) -> str:
    domestic = [h.replace("[국내] ", "") for h in highlights if h.startswith("[국내]")]
    global_  = [h.replace("[미국] ", "") for h in highlights if h.startswith("[미국]")]
    lines = []
    if domestic:
        lines.append("국내: " + " / ".join(d[:30] for d in domestic[:3]))
    if global_:
        lines.append("미국: " + " / ".join(g[:30] for g in global_[:3]))
    return "\n".join(lines) or "-"


def save_to_notion(briefing_data: dict) -> bool:
    token    = os.getenv("NOTION_API_TOKEN")
    db_id    = os.getenv("NOTION_DATABASE_ID")
    date_str = briefing_data.get("date", datetime.now().strftime("%Y-%m-%d"))

    if not token or not db_id:
        logging.error("[save_notion] .env에 NOTION_API_TOKEN / NOTION_DATABASE_ID 설정 필요")
        return False

    token = token.removeprefix("secret_")
    client = Client(auth=token, client=httpx.Client(verify=False))

    indicators = briefing_data.get("indicators", {})
    events     = briefing_data.get("events", [])
    highlights = briefing_data.get("highlights", [])

    try:
        page = client.pages.create(
            parent={"database_id": db_id},
            properties={
                "Name": {
                    "title": [{"type": "text", "text": {"content": f"{date_str} Market Brief"}}]
                },
                "날짜":     {"date": {"start": date_str}},
                "지표요약":  {"rich_text": _indicator_summary_rich(indicators)},
                "주요 이벤트": _prop_text(_events_summary(events)),
                "Briefing": _prop_text(_briefing_summary(highlights)),
            },
            children=_make_blocks(briefing_data),
        )
        logging.info(f"[save_notion] 저장 완료 - 페이지 ID: {page['id']}")
        return True

    except APIResponseError as e:
        logging.error(f"[save_notion] Notion API 오류: {e.code} - {e.body}")
        return False
    except Exception as e:
        logging.error(f"[save_notion] 예외 발생: {e}")
        return False


def _get_client():
    token = os.getenv("NOTION_API_TOKEN", "").removeprefix("secret_")
    return Client(auth=token, client=httpx.Client(verify=False))


def _find_today_page(client, db_id: str, date_str: str) -> str | None:
    """DB에서 date_str 날짜의 페이지 ID 반환. 없으면 None."""
    try:
        resp = client.databases.query(
            database_id=db_id,
            filter={"property": "날짜", "date": {"equals": date_str}},
        )
        results = resp.get("results", [])
        return results[0]["id"] if results else None
    except Exception as e:
        logging.error(f"[update_notion] 페이지 조회 실패: {e}")
        return None


def _delete_page_blocks(client, page_id: str):
    """페이지의 최상위 블록 전체 삭제 (페이지네이션 처리)."""
    cursor = None
    while True:
        kwargs = {"block_id": page_id}
        if cursor:
            kwargs["start_cursor"] = cursor
        resp = client.blocks.children.list(**kwargs)
        for block in resp.get("results", []):
            try:
                client.blocks.delete(block_id=block["id"])
            except Exception:
                pass
        if not resp.get("has_more"):
            break
        cursor = resp.get("next_cursor")


def update_notion(briefing_data: dict) -> bool:
    """오늘 날짜의 기존 페이지를 최신 데이터로 업데이트. 페이지 없으면 새로 생성."""
    token = os.getenv("NOTION_API_TOKEN")
    db_id = os.getenv("NOTION_DATABASE_ID")
    date_str = briefing_data.get("date", datetime.now().strftime("%Y-%m-%d"))

    if not token or not db_id:
        logging.error("[update_notion] .env에 NOTION_API_TOKEN / NOTION_DATABASE_ID 설정 필요")
        return False

    client = _get_client()
    page_id = _find_today_page(client, db_id, date_str)

    if not page_id:
        logging.info("[update_notion] 오늘 페이지 없음 - 새로 생성")
        return save_to_notion(briefing_data)

    indicators = briefing_data.get("indicators", {})
    events     = briefing_data.get("events", [])
    highlights = briefing_data.get("highlights", [])

    try:
        # 1. 기존 블록 전체 삭제 후 새 블록 추가
        _delete_page_blocks(client, page_id)
        new_blocks = _make_blocks(briefing_data)
        for i in range(0, len(new_blocks), 100):
            client.blocks.children.append(block_id=page_id, children=new_blocks[i:i+100])

        # 2. DB 속성 업데이트
        client.pages.update(
            page_id=page_id,
            properties={
                "지표요약":    {"rich_text": _indicator_summary_rich(indicators)},
                "주요 이벤트": _prop_text(_events_summary(events)),
                "Briefing":   _prop_text(_briefing_summary(highlights)),
            },
        )
        logging.info(f"[update_notion] 업데이트 완료 - 페이지 ID: {page_id}")
        return True

    except APIResponseError as e:
        logging.error(f"[update_notion] Notion API 오류: {e.code} - {e.body}")
        return False
    except Exception as e:
        logging.error(f"[update_notion] 예외 발생: {e}")
        return False
