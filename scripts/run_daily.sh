#!/bin/bash
# 매일 오전 7시 자동 실행용 스크립트
#
# crontab 등록 방법:
#   crontab -e
#   0 7 * * * /path/to/market-brief/scripts/run_daily.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
mkdir -p outputs

DATE=$(date +%Y-%m-%d)
OUTPUT_FILE="outputs/${DATE}.md"

echo "[$(date '+%H:%M')] 브리핑 생성 시작: $DATE"

claude "오늘 경제 뉴스 브리핑을 생성해줘" > "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
  echo "[$(date '+%H:%M')] 브리핑 저장 완료: $OUTPUT_FILE"
else
  echo "[$(date '+%H:%M')] 오류 발생. 재시도 중..."
  claude "오늘 경제 뉴스 브리핑을 생성해줘" > "$OUTPUT_FILE"
  if [ $? -ne 0 ]; then
    echo "# $DATE Market Brief - 생성 실패" > "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    echo "브리핑 자동 생성에 실패했습니다. 수동으로 확인이 필요합니다." >> "$OUTPUT_FILE"
    echo "[$(date '+%H:%M')] 재시도 실패. 실패 로그 저장: $OUTPUT_FILE"
  fi
fi
