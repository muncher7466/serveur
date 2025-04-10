@echo off
echo Lancement de l'application...

REM Vérifier si Python est installé
if not exist "C:\Users\muncher\AppData\Local\Programs\Python\Python313\python.exe" (
    echo Python n'est pas installé. Installation de Python 3.13...
    
    REM Télécharger l'installateur Python
    echo Téléchargement de Python 3.13...
    powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.13.0/python-3.13.0-amd64.exe' -OutFile 'python-installer.exe'}"
    
    REM Installer Python silencieusement
    echo Installation de Python...
    start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    
    REM Supprimer l'installateur
    del python-installer.exe
    
    REM Vérifier si l'installation a réussi
    if not exist "C:\Users\muncher\AppData\Local\Programs\Python\Python313\python.exe" (
        echo L'installation de Python a échoué. Veuillez installer Python manuellement depuis https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

REM Vérifier si pip est installé
"C:\Users\muncher\AppData\Local\Programs\Python\Python313\python.exe" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo pip n'est pas installé. Installation de pip...
    "C:\Users\muncher\AppData\Local\Programs\Python\Python313\python.exe" -m ensurepip --default-pip
)

REM Installer les dépendances si nécessaire
echo Installation des dépendances...
"C:\Users\muncher\AppData\Local\Programs\Python\Python313\python.exe" -m pip install -r requirements.txt

REM Créer le dossier data s'il n'existe pas
if not exist "data" mkdir data

REM Lancer l'application
echo Lancement de l'application...
"C:\Users\muncher\AppData\Local\Programs\Python\Python313\python.exe" app.py

pause
