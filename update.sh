#!/bin/bash

echo "========================================="
echo "Updating JemIn GitHub Repository"
echo "========================================="

read -p "Enter commit message (or press Enter for default): " message

if [ -z "$message" ]; then
    message="chore: update files"
fi

echo ""
echo "Staging all changes..."
git add .

echo ""
echo "Committing changes..."
git commit -m "$message"

echo ""
echo "Pushing to GitHub..."
git push origin master

echo ""
echo "========================================="
echo "Done! Your GitHub is now updated."
echo "========================================="
