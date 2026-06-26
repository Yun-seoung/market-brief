@echo off
REM Market Brief 일간 브리핑 자동 실행 스크립트
REM Windows Task Scheduler에서 호출됩니다.
REM
REM Task Scheduler 등록 명령 (PowerShell 관리자 권한으로 실행):
REM
REM   $trigger = New-ScheduledTaskTrigger -Daily -At "08:15AM"
REM   $action  = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c C:\Users\choik\OneDrive\Desktop\projects\market-brief\scripts\run_daily.bat"
REM   Register-ScheduledTask -TaskName "MarketBrief" -Trigger $trigger -Action $action -RunLevel Highest -Force
REM
REM 수동 테스트 실행:
REM   scripts\run_daily.bat

setlocal

REM ── 설정 ──────────────────────────────────────────────
set PROJECT_DIR=C:\Users\choik\OneDrive\Desktop\projects\market-brief
set PYTHON=python

REM Python 경로가 다르면 아래 줄 주석 해제 후 수정
REM set PYTHON=C:\Users\choik\AppData\Local\Programs\Python\Python312\python.exe

REM ── 실행 ──────────────────────────────────────────────
cd /d "%PROJECT_DIR%"

if not exist "outputs" mkdir outputs

echo [%date% %time%] Market Brief 시작
%PYTHON% main.py >> "outputs\scheduler.log" 2>&1

if %ERRORLEVEL% EQU 0 (
    echo [%date% %time%] 완료
) else (
    echo [%date% %time%] 오류 발생 - outputs\scheduler.log 확인
)

endlocal
