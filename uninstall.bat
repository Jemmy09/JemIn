@echo off
echo =========================================
echo Uninstalling JemIn
echo =========================================

echo Removing JemIn from Python...
pip uninstall jemin -y

echo.
echo Removing configuration and chat history files...
if exist "%USERPROFILE%\.jemin" (
    rmdir /s /q "%USERPROFILE%\.jemin"
    echo Data files removed successfully.
) else (
    echo No data files found.
)

echo.
echo =========================================
echo JemIn has been successfully uninstalled.
echo =========================================
pause
