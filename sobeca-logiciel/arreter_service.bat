@echo off
echo Arret du service Sobeca...

REM Arrêter tous les processus Python liés à l'application
taskkill /F /IM pythonw.exe /T 2>NUL
if "%ERRORLEVEL%"=="0" (
    echo Service arrete avec succes!
) else (
    echo Aucun service en cours d'execution n'a ete trouve.
)

echo.
echo Appuyez sur une touche pour fermer...
pause > nul
