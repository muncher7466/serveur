@echo off
echo Demarrage du service Sobeca en arriere-plan...

REM Vérifier si Python est déjà en cours d'exécution
tasklist /FI "IMAGENAME eq pythonw.exe" 2>NUL | find /I /N "pythonw.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo Le service est deja en cours d'execution.
    echo.
    echo Appuyez sur une touche pour fermer...
    pause > nul
    exit
)

REM Démarrer l'application en arrière-plan avec nohup
start /B "" "C:\Users\muncher\AppData\Local\Programs\Python\Python313\pythonw.exe" "%~dp0app.py" > nul 2>&1

REM Attendre un peu pour s'assurer que le service démarre
timeout /t 2 > nul

echo Service demarre avec succes!
echo L'application est accessible sur http://localhost:5000
echo Le service continuera de fonctionner en arriere-plan.
echo.
echo Appuyez sur une touche pour fermer cette fenetre...
pause > nul
