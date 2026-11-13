@echo off
rem Inicia a API FastAPI (somente em 127.0.0.1).
rem Uso: scripts\iniciar_backend.bat            (normal)
rem      scripts\iniciar_backend.bat --reload   (recarrega ao editar o codigo)
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
title Quem Faz - Backend (API :8000)

if not exist ".venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual nao encontrado. Execute na raiz do projeto:
    echo        py -3 -m venv .venv
    echo        .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    pause
    exit /b 1
)

netstat -ano | findstr /r /c:":8000 .*LISTENING" >nul
if %errorlevel%==0 (
    echo [AVISO] A porta 8000 ja esta em uso.
    echo         Provavelmente o backend ja esta aberto em outra janela - feche-a antes,
    echo         ou acesse direto http://127.0.0.1:8000/docs
    pause
    exit /b 1
)

set "EXTRA="
if /i "%~1"=="--reload" set "EXTRA=--reload --reload-dir backend"

echo.
echo  API:          http://127.0.0.1:8000
echo  Documentacao: http://127.0.0.1:8000/docs
echo  Para encerrar: Ctrl+C
echo.
".venv\Scripts\python.exe" -m uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8000 %EXTRA%

echo.
echo O backend foi encerrado.
pause
