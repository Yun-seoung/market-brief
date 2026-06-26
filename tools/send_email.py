import logging
import os
import smtplib
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_SMTP_HOST = "smtp.naver.com"
_SMTP_PORT = 465


def _build_body(briefing_data: dict) -> str:
    """메일 본문: 핵심 3줄 요약 + 주요 지표."""
    date_str   = briefing_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    highlights = briefing_data.get("highlights", [])
    indicators = briefing_data.get("indicators", {})

    lines = [f"[Market Brief] {date_str}\n", "── 오늘의 핵심 ──────────────────────"]
    for i, h in enumerate(highlights[:3], 1):
        lines.append(f"{i}. {h}")

    lines.append("\n── 주요 지표 ────────────────────────")
    key_display = {
        "S&P500": "S&P500", "NASDAQ": "NASDAQ", "KOSPI": "KOSPI",
        "원달러환율": "원달러", "VIX": "VIX",
    }
    for label, key in key_display.items():
        data = indicators.get(label, {})
        if data.get("current"):
            sign = "+" if (data.get("change") or 0) >= 0 else ""
            lines.append(
                f"  {label:10s} {data['current']:>10,.2f}  "
                f"({sign}{data.get('change_pct', 0):.2f}%)"
            )

    lines.append("\n자세한 내용은 첨부 PDF를 확인하세요.")
    return "\n".join(lines)


def send_briefing_email(briefing_data: dict, pdf_path: str) -> bool:
    """네이버 SMTP로 브리핑 메일 발송. 성공 시 True, 실패 시 False."""
    smtp_user = os.getenv("NAVER_SMTP_USER")
    smtp_pw   = os.getenv("NAVER_SMTP_PASSWORD")
    mail_to   = os.getenv("NAVER_MAIL_TO")

    if not all([smtp_user, smtp_pw, mail_to]):
        logging.error("[send_email] .env에 NAVER_SMTP_USER / NAVER_SMTP_PASSWORD / NAVER_MAIL_TO 설정 필요")
        return False

    date_str = briefing_data.get("date", datetime.now().strftime("%Y-%m-%d"))
    subject  = f"[Market Brief] {date_str}"
    body     = _build_body(briefing_data)

    msg = MIMEMultipart()
    msg["From"]    = smtp_user
    msg["To"]      = mail_to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    # PDF 첨부
    pdf_file = Path(pdf_path)
    if pdf_file.exists():
        with open(pdf_file, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{pdf_file.name}"',
        )
        msg.attach(part)
    else:
        logging.warning(f"[send_email] PDF 파일 없음: {pdf_path}")

    try:
        with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT) as server:
            server.login(smtp_user, smtp_pw)
            server.sendmail(smtp_user, mail_to, msg.as_string())
        logging.info(f"[send_email] 발송 완료 → {mail_to}")
        return True
    except smtplib.SMTPAuthenticationError:
        logging.error("[send_email] 인증 실패 - 네이버 앱 비밀번호 확인 필요 (일반 로그인 비밀번호 아님)")
        return False
    except Exception as e:
        logging.error(f"[send_email] 발송 실패: {e}")
        return False
