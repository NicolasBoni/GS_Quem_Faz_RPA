@echo off
rem Abre backend (8000) e frontend (8080) em janelas do CMD e depois o navegador.
rem Uso: duplo clique ou scripts\iniciar.bat
setlocal
chcp 65001 >nul
cd /d "%~dp0.."

rem So abre cada servidor se a porta dele ainda estiver livre (evita duas copias).
netstat -ano | findstr /r /c:":8000 .*LISTENING" >nul
if %errorlevel%==0 (
    echo Backend ja esta em execucao na porta 8000 - nao sera aberto de novo.
) else (
    start "Quem Faz - Backend (API :8000)" cmd /k ""%~dp0iniciar_backend.bat""
)
netstat -ano | findstr /r /c:":8080 .*LISTENING" >nul
if %errorlevel%==0 (
    echo Frontend ja esta em execucao na porta 8080 - nao sera aberto de novo.
) else (
    start "Quem Faz - Frontend (PHP :8080)" cmd /k ""%~dp0iniciar_frontend.bat""
)

echo Aguardando a API responder...
set /a TENTATIVAS=0
:espera
set /a TENTATIVAS+=1
curl -s -o nul -m 2 http://127.0.0.1:8000/api/health && goto pronto
if %TENTATIVAS% geq 30 goto sem_resposta
timeout /t 1 /nobreak >nul
goto espera

:pronto
echo API pronta.
goto abrir

:sem_resposta
echo A API ainda nao respondeu. Confira a janela "Quem Faz - Backend".

:abrir
start "" http://127.0.0.1:8080
endlocal
