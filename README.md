# 📊 Market Brief

> 매일 아침 8시 15분, 경제 뉴스를 자동으로 수집·정리해서 노션에 저장하고 네이버 메일로 PDF 브리핑을 발송하는 AI 에이전트 시스템

<br>

## 🎯 프로젝트 개요

바쁜 아침, 경제 뉴스를 일일이 찾아보는 시간을 없애기 위해 만든 자동화 파이프라인입니다.  
Claude Code 기반 AI 에이전트가 뉴스 수집부터 메일 발송까지 전 과정을 자동으로 처리합니다.

<br>

## ✨ 주요 기능

- 📰 **경제 뉴스 자동 수집** — 국내외 주요 경제 이슈, 오늘 예정 이벤트(FOMC 등)
- 📈 **실시간 경제 지표** — S&P500, NASDAQ, KOSPI, KOSDAQ, 원달러환율 등 9개 지표
- 🗂️ **Notion 자동 저장** — 날짜별 페이지로 누적 저장, 표·섹션 구조화
- 📄 **PDF 리포트 생성** — 한국어 폰트 지원, 깔끔한 레이아웃
- 📧 **네이버 메일 자동 발송** — 매일 08:15 PDF 첨부 발송
- ⏰ **완전 자동화** — cron 기반 스케줄링, 무인 실행

<br>

## 🏗️ 시스템 구조

```
Workflow (업무 매뉴얼)
    ↓
Agent = Claude Code (판단 및 조율)
    ↓
Tools (실제 실행)
    ├── collect_news.py     뉴스 & 지표 수집
    ├── save_notion.py      Notion API 블록 저장
    ├── generate_pdf.py     PDF 생성
    └── send_email.py       네이버 SMTP 발송
```

<br>

## 📁 디렉토리 구조

```
market-brief/
├── CLAUDE.md                   # AI 에이전트 행동 지침서
├── .env.example                # 환경변수 예시
├── .gitignore
├── requirements.txt
├── workflows/
│   ├── daily-briefing.md       # 전체 실행 흐름
│   ├── collect-news.md         # 뉴스 수집 워크플로우
│   └── format-report.md        # 브리핑 포맷 정의
├── tools/
│   ├── collect_news.py
│   ├── save_notion.py
│   ├── generate_pdf.py
│   └── send_email.py
├── agents/
│   ├── research-coordinator.md
│   ├── search-specialist.md
│   └── data-researcher.md
└── outputs/                    # 생성된 PDF 저장
```

<br>

## 🚀 설치 및 실행

### 1. 저장소 클론
```bash
git clone https://github.com/yun-seoung/market-brief.git
cd market-brief
```

### 2. 패키지 설치
```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정
```bash
cp .env.example .env
# .env 파일 열어서 각 값 입력
```

```env
BRIGHTDATA_API_TOKEN=     # Brightdata API 토큰 (없으면 공란)
NAVER_SMTP_USER=          # 네이버 아이디@naver.com
NAVER_SMTP_PASSWORD=      # 네이버 앱 비밀번호 (12자리)
NAVER_MAIL_TO=            # 수신 메일 주소
NOTION_API_TOKEN=         # Notion Integration 토큰
NOTION_DATABASE_ID=       # Notion 데이터베이스 ID
```

### 4. 수동 실행
```bash
claude "오늘 경제 뉴스 브리핑 만들어줘"
```

### 5. 자동 실행 설정 (매일 08:15)
```bash
crontab -e
# 아래 줄 추가
15 8 * * * cd /path/to/market-brief && claude "오늘 경제 뉴스 브리핑 만들어줘"
```

<br>

## 📋 브리핑 예시

```
📊 오늘의 핵심 요약
1. 연준, 금리 동결 결정 — 시장 예상에 부합
2. KOSPI 2,600선 회복 — 외국인 순매수 전환
3. 원달러환율 1,350원대 안정화

📈 경제 지표
| 지표       | 현재값    | 전일대비 |
|------------|-----------|---------|
| S&P500     | 5,123     | +0.3%   |
| KOSPI      | 2,612     | +1.2%   |
| 원달러환율  | 1,351     | -0.2%   |
...

🇰🇷 국내 경제
📅 오늘 예정 이벤트
```

<br>

## 🛠️ 기술 스택

| 분류 | 기술 |
|------|------|
| AI 에이전트 | Claude Code (Anthropic) |
| 언어 | Python 3.11+ |
| 데이터 수집 | Brightdata MCP, requests, BeautifulSoup4 |
| 저장 | Notion API |
| 메일 | SMTP (naver.com) |
| PDF | ReportLab / WeasyPrint |
| 스케줄링 | cron |

<br>

## ⚠️ 주의사항

- `.env` 파일은 절대 GitHub에 올리지 마세요 (`.gitignore`에 포함됨)
- 네이버 메일은 일반 비밀번호가 아닌 **앱 비밀번호** 사용
- Notion Integration에 데이터베이스 접근 권한 부여 필요

<br>

## 📌 개발 배경

매일 아침 경제 뉴스를 여러 사이트에서 수동으로 찾아보는 번거로움을 없애고자 제작했습니다.  
Claude Code의 AI 에이전트 기능과 Workflow → Agent → Tool 3단계 구조를 활용해  
유지보수가 쉽고 확장 가능한 자동화 시스템을 구현했습니다.

<br>

---

> Made with Claude Code
