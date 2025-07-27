@echo off
setlocal enabledelayedexpansion

:: === CONFIGURATIONS ===
set "DASHBOARD_NAME=MT4Dashboard"
set "PROJECT_PATH=%~dp0"
set "TARGET_PATH=%PROJECT_PATH%DATA"
set "MT4_PATH=C:\Users\1234\AppData\Roaming\MetaQuotes\Terminal\2C68BEE3A904BDCEE3EEF5A5A77EC162\MQL4"
set "MT4_FILES=%MT4_PATH%\Files"
set "SYMLINK_NAME=DATA"
set "HOSTS_FILE=C:\Windows\System32\drivers\etc\hosts"
set "HOSTS_ENTRY=127.0.0.1 local.host"

:: === CAPITAL DÉCLARÉ (à modifier si besoin) ===
set "STARTING_BALANCE=10000"

:: === PYTHON MANUEL (optionnel) ===
set "PythonLocation="

:: === COULEURS ===
set "COLOR_SUCCESS=0A"
set "COLOR_ERROR=0C"
set "COLOR_INFO=0B"

:: === AFFICHAGE ENTÊTE ===
color %COLOR_INFO%
echo ==========================
echo CONFIGURATION DASHBOARD
echo ==========================

:: === Vérification/modification du fichier hosts ===
echo [INFO] Vérification du fichier hosts...
set "hostsEntryFound=0"

:: Vérifier les droits d'administration
net session >nul 2>&1
if %ERRORLEVEL% neq 0 (
    color %COLOR_ERROR%
    echo [ERREUR] Ce script nécessite des droits administrateur pour modifier le fichier hosts.
    echo Veuillez exécuter en tant qu'administrateur.
    pause
    exit /b
)

:: Vérifier si l'entrée existe déjà
find /c "%HOSTS_ENTRY%" "%HOSTS_FILE%" >nul
if %ERRORLEVEL% equ 0 (
    color %COLOR_SUCCESS%
    echo [OK] L'entrée "%HOSTS_ENTRY%" existe déjà dans le fichier hosts.
    color %COLOR_INFO%
    set "hostsEntryFound=1"
)

:: Ajouter l'entrée si elle n'existe pas
if %hostsEntryFound% equ 0 (
    echo [INFO] Ajout de l'entrée "%HOSTS_ENTRY%" dans le fichier hosts...
    
    echo. >> "%HOSTS_FILE%"
    echo # Added by %DASHBOARD_NAME% configuration >> "%HOSTS_FILE%"
    echo %HOSTS_ENTRY% >> "%HOSTS_FILE%"
    
    find /c "%HOSTS_ENTRY%" "%HOSTS_FILE%" >nul
    if %ERRORLEVEL% equ 0 (
        color %COLOR_SUCCESS%
        echo [OK] Entrée ajoutée avec succès dans le fichier hosts.
        color %COLOR_INFO%
    ) else (
        color %COLOR_ERROR%
        echo [ERREUR] Impossible d'ajouter l'entrée dans le fichier hosts.
        echo Veuillez vérifier manuellement le fichier %HOSTS_FILE%
        pause
    )
)

:: === Vérification du dossier Files MT4 ===
if not exist "%MT4_FILES%" (
    color %COLOR_ERROR%
    echo [ERREUR] Le dossier %MT4_FILES% est introuvable.
    echo Vérifiez que MT4 est installé et que le chemin est correct.
    pause
    exit /b
)

:: === Vérification dossier cible DATA ===
if not exist "%TARGET_PATH%" (
    color %COLOR_ERROR%
    echo [ERREUR] Le dossier cible %TARGET_PATH% est introuvable.
    echo Veuillez créer ce dossier avant de continuer.
    pause
    exit /b
)

:: === Suppression ancien lien symbolique ou dossier ===
if exist "%MT4_FILES%\%SYMLINK_NAME%" (
    echo [INFO] Suppression ancien lien symbolique ou dossier...
    rmdir /S /Q "%MT4_FILES%\%SYMLINK_NAME%"
    if exist "%MT4_FILES%\%SYMLINK_NAME%" (
        color %COLOR_ERROR%
        echo [ERREUR] Impossible de supprimer le lien ou dossier. Fermez MT4 et réessayez.
        pause
        exit /b
    ) else (
        color %COLOR_SUCCESS%
        echo [OK] Ancien lien ou dossier supprimé.
        color %COLOR_INFO%
    )
) else (
    echo [INFO] Aucun ancien lien ou dossier à supprimer.
)

:: === Création lien symbolique ===
echo [INFO] Création du lien symbolique...
mklink /D "%MT4_FILES%\%SYMLINK_NAME%" "%TARGET_PATH%" >nul 2>&1

if %ERRORLEVEL% NEQ 0 (
    color %COLOR_ERROR%
    echo [ERREUR] Échec de la création du lien symbolique.
    echo Essayez d'exécuter ce script en tant qu'administrateur.
    pause
    exit /b
) else (
    color %COLOR_SUCCESS%
    echo [OK] Lien symbolique créé : "%MT4_FILES%\%SYMLINK_NAME%" -> "%TARGET_PATH%"
    color %COLOR_INFO%
)

:: === Ajout variables d'environnement MT4_DASHBOARD et MT4_DASHBOARD_BALANCE ===
echo [INFO] Ajout variables d'environnement...
setx MT4_DASHBOARD "%PROJECT_PATH%" >nul 2>&1
setx MT4_DASHBOARD_BALANCE "%STARTING_BALANCE%" >nul 2>&1

if %ERRORLEVEL% EQU 0 (
    color %COLOR_SUCCESS%
    echo [OK] MT4_DASHBOARD et MT4_DASHBOARD_BALANCE définies à :
    echo     MT4_DASHBOARD=%PROJECT_PATH%
    echo     MT4_DASHBOARD_BALANCE=%STARTING_BALANCE%
    color %COLOR_INFO%
) else (
    color %COLOR_ERROR%
    echo [ERREUR] Impossible d'ajouter les variables d'environnement.
)

:: === Accès à Python ===
if not "%PythonLocation%"=="" (
    echo [INFO] Python forcé : "%PythonLocation%"
    set "PY_CMD=%PythonLocation%"
) else (
    where py >nul 2>&1
    if errorlevel 1 (
        goto check_python_exe
    )

    for /f "usebackq tokens=*" %%v in (`py -3.13 --version 2^>^&1`) do set "PY_VER=%%v"
    echo !PY_VER! | findstr /i "Python 3.13" >nul
    if errorlevel 1 (
        goto check_python_exe
    ) else (
        echo [OK] Python 3.13 détecté via 'py'
        set "PY_CMD=py -3.13"
        goto python_found
    )

    :check_python_exe
    for /f "usebackq tokens=*" %%v in (`python --version 2^>^&1`) do set "PY_VER=%%v"
    echo !PY_VER! | findstr /i "Python 3.13" >nul
    if errorlevel 1 (
        color %COLOR_ERROR%
        echo [ERREUR] Python 3.13 non détecté automatiquement.
        echo -> Vous pouvez configurer manuellement la variable 'PythonLocation' dans ce script.
        echo -> Exemple : set "PythonLocation=C:\Python313\python.exe"
        pause
        exit /b
    ) else (
        echo [OK] Python 3.13 détecté via 'python'
        set "PY_CMD=python"
    )
)

:python_found
echo [INFO] Installation des dépendances Python...
cd /d "%PROJECT_PATH%SERVER"
%PY_CMD% -m pip install --upgrade pip >nul 2>&1
%PY_CMD% -m pip install -r "%PROJECT_PATH%requirements.txt"

if %ERRORLEVEL% NEQ 0 (
    color %COLOR_ERROR%
    echo [ERREUR] Installation des dépendances échouée.
    pause
    exit /b
)

:: === LANCEMENT SERVEUR PYTHON ===
echo [INFO] Lancement du serveur Flask dans la même console...
%PY_CMD% main.py

:: === FIN ===
pause
exit /b