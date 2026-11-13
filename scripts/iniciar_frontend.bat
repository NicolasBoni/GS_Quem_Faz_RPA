@echo off
rem Inicia o frontend PHP com o servidor embutido (somente em 127.0.0.1).
rem Uso: scripts\iniciar_frontend.bat
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
title Quem Faz - Frontend (PHP :8080)

set "PHP="
where php >nul 2>nul && set "PHP=php"
if not defined PHP if exist "tools\php\php.exe" set "PHP=tools\php\php.exe"
if not defined PHP (
    echo [ERRO] PHP 8.2+ nao encontrado.
    echo        Instale com: winget install PHP.PHP.8.3
    echo        ou extraia o zip oficial de https://windows.php.net em tools\php
    pause
    exit /b 1
)

netstat -ano | findstr /r /c:":8080 .*LISTENING" >nul
if %errorlevel%==0 (
    echo [AVISO] A porta 8080 ja esta em uso.
    echo         Provavelmente o frontend ja esta aberto em outra janela - feche-a antes,
    echo         ou acesse direto http://127.0.0.1:8080
    pause
    exit /b 1
)

echo.
echo  Frontend: http://127.0.0.1:8080
echo  Para encerrar: Ctrl+C
echo.
"%PHP%" -S 127.0.0.1:8080 -t frontend

echo.
echo O frontend foi encerrado.
pause
