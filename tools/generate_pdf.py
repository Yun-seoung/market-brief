import contextlib
import logging
import os
from datetime import datetime
from pathlib import Path

from fpdf import FPDF

# fonttools 로그를 루트 로거에 전파하지 않고 NullHandler로 버림
_ft_logger = logging.getLogger("fontTools")
_ft_logger.addHandler(logging.NullHandler())
_ft_logger.propagate = False


@contextlib.contextmanager
def _quiet_fonttools():
    """사용처에서 명시적으로 감싸고 싶을 때 사용 (현재는 module-level 억제로 충분)."""
    yield

# ── 색상 팔레트 ──────────────────────────────────────────────
COLOR_HEADER_BG   = (15, 52, 96)    # 진한 네이비
COLOR_HEADER_TEXT = (255, 255, 255) # 흰색
COLOR_SECTION_BG  = (230, 236, 245) # 연한 파랑
COLOR_SECTION_TEXT = (15, 52, 96)
COLOR_BODY        = (40, 40, 40)
COLOR_ACCENT      = (220, 53, 69)   # 빨강 (하락)
COLOR_POSITIVE    = (40, 167, 69)   # 초록 (상승)
COLOR_BORDER      = (200, 200, 200)

# ── 폰트 경로 (Windows Malgun Gothic) ────────────────────────
_FONT_PATHS = [
    r"C:\Windows\Fonts\malgun.ttf",      # Malgun Gothic Regular
    r"C:\Windows\Fonts\malgunbd.ttf",    # Malgun Gothic Bold
]


class BriefingPDF(FPDF):
    def __init__(self, date_str: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.date_str = date_str
        self._font_name = self._load_font()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(left=15, top=15, right=15)

    def _load_font(self) -> str:
        """Malgun Gothic 로드. 실패 시 Helvetica(기본 ASCII 폰트) 사용."""
        if os.path.exists(_FONT_PATHS[0]):
            self.add_font("Malgun", style="", fname=_FONT_PATHS[0])
            if os.path.exists(_FONT_PATHS[1]):
                self.add_font("Malgun", style="B", fname=_FONT_PATHS[1])
            return "Malgun"
        logging.warning("[generate_pdf] 맑은 고딕 폰트를 찾을 수 없습니다. Helvetica 사용.")
        return "Helvetica"

    def header(self):
        # 헤더 배경
        self.set_fill_color(*COLOR_HEADER_BG)
        self.rect(0, 0, 210, 22, style="F")
        # 제목
        self.set_font(self._font_name, style="B", size=13)
        self.set_text_color(*COLOR_HEADER_TEXT)
        self.set_xy(15, 6)
        self.cell(130, 10, "Market Brief", ln=0)
        # 날짜
        self.set_font(self._font_name, size=10)
        self.set_xy(150, 6)
        self.cell(45, 10, self.date_str, align="R", ln=1)
        self.set_text_color(*COLOR_BODY)
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font(self._font_name, size=8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"수집 시각: {datetime.now().strftime('%H:%M')}  |  자동 생성 브리핑", align="C")

    def section_title(self, title: str):
        self.set_fill_color(*COLOR_SECTION_BG)
        self.set_text_color(*COLOR_SECTION_TEXT)
        self.set_font(self._font_name, style="B", size=11)
        self.cell(0, 8, f"  {title}", ln=1, fill=True)
        self.set_text_color(*COLOR_BODY)
        self.ln(1)

    def bullet_item(self, title: str, summary: str, source: str, link: str):
        self.set_font(self._font_name, style="B", size=9)
        self.set_x(18)
        self.multi_cell(0, 5, f"• {title}", ln=1)
        if summary:
            self.set_font(self._font_name, size=8)
            self.set_text_color(80, 80, 80)
            self.set_x(22)
            self.multi_cell(0, 4, summary, ln=1)
            self.set_text_color(*COLOR_BODY)
        self.set_font(self._font_name, size=7)
        self.set_text_color(100, 100, 200)
        self.set_x(22)
        self.cell(0, 4, f"출처: {source}", link=link, ln=1)
        self.set_text_color(*COLOR_BODY)
        self.ln(1)

    def event_item(self, time: str, currency: str, impact: str, event: str):
        impact_label = {"high": "[★★★]", "medium": "[★★☆]", "low": "[★☆☆]"}.get(impact, "[   ]")
        self.set_font(self._font_name, size=9)
        self.set_x(18)
        self.cell(18, 5, time, ln=0)
        self.cell(12, 5, currency, ln=0)
        self.set_font(self._font_name, style="B", size=9)
        self.cell(20, 5, impact_label, ln=0)
        self.set_font(self._font_name, size=9)
        self.multi_cell(0, 5, event, ln=1)

    def indicator_table(self, indicators: dict):
        us_keys   = ["S&P500", "NASDAQ", "DOW", "달러인덱스", "미국채10년", "VIX"]
        kr_keys   = ["KOSPI", "KOSDAQ", "원달러환율"]

        for group_label, keys in [("미국 시장", us_keys), ("한국 시장", kr_keys)]:
            self.set_font(self._font_name, style="B", size=9)
            self.set_x(18)
            self.cell(0, 5, group_label, ln=1)
            self.set_draw_color(*COLOR_BORDER)

            col_w = [35, 28, 28, 30]
            self.set_fill_color(240, 240, 240)
            self.set_font(self._font_name, style="B", size=8)
            self.set_x(18)
            for header, w in zip(["지표", "현재값", "전일 대비", "등락률(%)"], col_w):
                self.cell(w, 6, header, border=1, align="C", fill=True)
            self.ln()

            self.set_font(self._font_name, size=8)
            for key in keys:
                data = indicators.get(key, {})
                current   = f"{data.get('current', '-'):,.2f}" if data.get("current") else "-"
                change    = data.get("change")
                change_pct = data.get("change_pct")

                if change is not None:
                    sign = "+" if change >= 0 else ""
                    change_str = f"{sign}{change:,.2f}"
                    pct_str    = f"{sign}{change_pct:.2f}%"
                    if change >= 0:
                        self.set_text_color(*COLOR_POSITIVE)
                    else:
                        self.set_text_color(*COLOR_ACCENT)
                else:
                    change_str = "-"
                    pct_str = "-"

                self.set_x(18)
                self.cell(col_w[0], 5, key, border=1)
                self.set_text_color(*COLOR_BODY)
                self.cell(col_w[1], 5, current, border=1, align="R")
                if change is not None and change >= 0:
                    self.set_text_color(*COLOR_POSITIVE)
                elif change is not None:
                    self.set_text_color(*COLOR_ACCENT)
                self.cell(col_w[2], 5, change_str, border=1, align="R")
                self.cell(col_w[3], 5, pct_str, border=1, align="R")
                self.set_text_color(*COLOR_BODY)
                self.ln()
            self.ln(3)


def create_pdf(briefing_data: dict, output_dir: str = "outputs") -> str:
    """브리핑 데이터를 받아 PDF 파일을 생성하고 저장 경로를 반환."""
    date_str   = briefing_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    indicators = briefing_data.get("indicators", {})
    news       = briefing_data.get("news", [])
    events     = briefing_data.get("events", [])
    highlights = briefing_data.get("highlights", [])

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    output_path = str(Path(output_dir) / f"{date_str}_market_brief.pdf")

    pdf = BriefingPDF(date_str=date_str)
    pdf.add_page()

    # ── 1. 오늘의 핵심 ──────────────────────────────────────
    pdf.section_title("오늘의 핵심")
    pdf.set_font(pdf._font_name, size=9)
    for i, line in enumerate(highlights[:3], 1):
        pdf.set_x(18)
        pdf.multi_cell(0, 5, f"{i}. {line}", ln=1)
    pdf.ln(3)

    # ── 2. 전날 주요 경제 사건 ────────────────────────────
    pdf.section_title("전날 주요 경제 사건")
    if news:
        for item in news[:8]:
            pdf.bullet_item(
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                source=item.get("source", ""),
                link=item.get("link", ""),
            )
    else:
        pdf.set_x(18)
        pdf.set_font(pdf._font_name, size=9)
        pdf.cell(0, 5, "뉴스 데이터 없음", ln=1)
    pdf.ln(2)

    # ── 3. 오늘 예정 이벤트 ──────────────────────────────
    pdf.section_title("오늘 예정된 이벤트")
    if events:
        for ev in events[:10]:
            pdf.event_item(
                time=ev.get("time", ""),
                currency=ev.get("currency", ""),
                impact=ev.get("impact", ""),
                event=ev.get("event", ""),
            )
    else:
        pdf.set_x(18)
        pdf.set_font(pdf._font_name, size=9)
        pdf.cell(0, 5, "예정 이벤트 없음 또는 수집 실패", ln=1)
    pdf.ln(2)

    # ── 4. 경제 지표 ─────────────────────────────────────
    pdf.section_title("경제 지표")
    pdf.indicator_table(indicators)

    with _quiet_fonttools():
        pdf.output(output_path)
    logging.info(f"[generate_pdf] 저장 완료: {output_path}")
    return output_path


if __name__ == "__main__":
    sample = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "highlights": [
            "S&P500 0.3% 상승, KOSPI 0.5% 상승 마감",
            "Fed 금리 동결 결정 — 다음 회의는 7월 예정",
            "원달러 환율 1,380원 유지, 달러 강세 지속",
        ],
        "news": [
            {"title": "Fed, 기준금리 동결 결정", "summary": "연방준비제도가 5.25% 금리를 유지하기로 결정했다.", "source": "Reuters", "link": "https://reuters.com"},
            {"title": "코스피 2,780 마감", "summary": "외국인 순매수에 힘입어 소폭 상승 마감.", "source": "연합뉴스", "link": "https://yna.co.kr"},
        ],
        "events": [
            {"time": "21:30", "currency": "USD", "impact": "high", "event": "U.S. Initial Jobless Claims", "forecast": "220K", "previous": "218K"},
            {"time": "10:00", "currency": "KRW", "impact": "medium", "event": "한국은행 금통위 회의", "forecast": "", "previous": ""},
        ],
        "indicators": {
            "S&P500":    {"current": 5300.12, "change": 15.3, "change_pct": 0.29},
            "NASDAQ":    {"current": 16800.0, "change": -20.0, "change_pct": -0.12},
            "DOW":       {"current": 39200.0, "change": 80.0, "change_pct": 0.20},
            "달러인덱스": {"current": 104.5, "change": 0.1, "change_pct": 0.10},
            "미국채10년": {"current": 4.35, "change": -0.02, "change_pct": -0.46},
            "VIX":       {"current": 14.2, "change": -0.3, "change_pct": -2.07},
            "KOSPI":     {"current": 2780.5, "change": 13.5, "change_pct": 0.49},
            "KOSDAQ":    {"current": 850.2, "change": -2.1, "change_pct": -0.25},
            "원달러환율": {"current": 1382.5, "change": 2.5, "change_pct": 0.18},
        },
    }
    path = create_pdf(sample)
    print(f"테스트 PDF 생성: {path}")
