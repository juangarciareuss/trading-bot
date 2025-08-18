@echo off
echo.
echo --- 1. Preparando todos los cambios (git add .) ---
git add .

echo.
echo --- 2. Creando el commit (paquete de cambios)... ---
set /p commit_message="Escribe un mensaje para el commit y presiona Enter: "
git commit -m "%commit_message%"

echo.
echo --- 3. Subiendo los cambios a GitHub (git push)... ---
git push origin main

echo.
echo --- Proceso completado. ---
pause