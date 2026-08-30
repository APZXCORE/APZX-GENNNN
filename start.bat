@echo off
title APZX G3NNNN
where python >nul 2>&1 && set PY_CMD=python || set PY_CMD=py
%PY_CMD% start.py %*
pause
