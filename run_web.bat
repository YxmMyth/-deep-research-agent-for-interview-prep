@echo off
REM 设置 UTF-8 编码
set PYTHONIOENCODING=utf-8
chcp 65001 > nul

REM 启动 Streamlit
python -m streamlit run web_app.py --server.headless true
