@echo off
chcp 65001 >nul
setlocal
title GestaoAxia
cd /d "%~dp0"

echo.
echo  ==========================================
echo     GestaoAxia - iniciando o sistema local
echo  ==========================================
echo.

where python >nul 2>nul || (echo [ERRO] Python nao encontrado. Instale o Python 3.12+ em python.org & pause & exit /b 1)
where npm >nul 2>nul || (echo [ERRO] Node.js nao encontrado. Instale o Node.js LTS em nodejs.org & pause & exit /b 1)

rem --- configuracao local (backend\.env) ---
if not exist "backend\.env" (
  copy "backend\.env.example" "backend\.env" >nul
  echo [AVISO] Criei backend\.env a partir do modelo.
  echo         Abra esse arquivo, ajuste ADMIN_EMAIL, ADMIN_SENHA e SECRET_KEY e rode de novo.
  notepad "backend\.env"
  pause
  exit /b 0
)

rem --- dependencias do backend ---
echo [1/4] Conferindo dependencias do Python...
python -c "import fastapi, sqlalchemy, jwt, bcrypt, openpyxl, email_validator" >nul 2>nul || (
  python -m pip install -r backend\requirements.txt || (echo [ERRO] Falha ao instalar dependencias Python & pause & exit /b 1)
)

rem --- frontend ---
echo [2/4] Preparando as telas (React)...
if not exist "frontend\node_modules" (
  pushd frontend
  call npm install || (popd & echo [ERRO] Falha no npm install & pause & exit /b 1)
  popd
)
pushd frontend
call npm run build >nul || (popd & echo [ERRO] Falha ao compilar o frontend & pause & exit /b 1)
popd

rem --- banco: importa as planilhas na primeira vez ---
echo [3/4] Conferindo banco de dados...
pushd backend
if not exist "..\dados\gestaoaxia.db" (
  echo       Banco vazio: importando as planilhas da pasta do projeto...
  python -m app.importar --pasta ..
)
popd

rem --- servidor ---
echo [4/4] Abrindo em http://localhost:8000  (feche esta janela para desligar)
echo.
set "FRONTEND_DIST=%~dp0frontend\dist"
if not defined GESTAOAXIA_SEM_NAVEGADOR start "" /b cmd /c "timeout /t 3 >nul & start http://localhost:8000"
pushd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
popd
pause
