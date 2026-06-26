@echo off
cd /d "C:\Users\choik\OneDrive\Desktop\projects\market-brief"
"C:\Users\choik\AppData\Local\Python\pythoncore-3.14-64\python.exe" main.py --update --skip-email >> outputs\update.log 2>&1
