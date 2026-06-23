@echo off
echo =========================================
echo Updating JemIn GitHub Repository
echo =========================================

set /p message="Enter commit message (or press Enter for default): "

if "%message%"=="" (
    set message="chore: update files"
)

set GIT_PATH="C:\Program Files\Git\cmd\git.exe"

echo.
echo Staging all changes...
%GIT_PATH% add .

echo.
echo Committing changes...
%GIT_PATH% commit -m "%message%"

echo.
echo Pushing to GitHub...
%GIT_PATH% push origin master

echo.
echo =========================================
echo Done! Your GitHub is now updated.
echo =========================================
pause
