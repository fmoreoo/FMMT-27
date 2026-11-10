@echo off
rem Starts the FMMT 27 reader and opens the tool in your browser.
rem Keep this window open while you use the tool; close it to stop.
cd /d "%~dp0reader"
python server.py
if errorlevel 1 pause
