#!/bin/bash

echo "========================================="
echo "Uninstalling JemIn"
echo "========================================="

echo "Removing JemIn from Python..."
pip uninstall jemin -y

echo ""
echo "Removing configuration and chat history files..."
if [ -d "$HOME/.jemin" ]; then
    rm -rf "$HOME/.jemin"
    echo "Data files removed successfully."
else
    echo "No data files found."
fi

echo ""
echo "========================================="
echo "JemIn has been successfully uninstalled."
echo "========================================="
