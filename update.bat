@echo off
echo =========================================
echo Updating JemIn GitHub Repository
echo =========================================

set /p message="Enter commit message (or press Enter for default): "

if "%message%"=="" (
    set message="chore: update files"
)

echo.
echo Staging all changes...
git add .

echo.
echo Committing changes...
git commit -m "%message%"

echo.
echo Pushing to GitHub...
git push origin master

echo.
echo =========================================
echo Done! Your GitHub is now updated.
echo =========================================
pause
