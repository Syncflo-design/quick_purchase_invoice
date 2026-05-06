@echo off
REM Pushes quick_purchase_invoice to https://github.com/Syncflo-design/quick_purchase_invoice
REM Run from anywhere; this script cd's to the right folder.

cd /d C:\ClaudeCode\CoWork_Helper\projects\quick_purchase_invoice || exit /b 1

if not exist .git (
    git init || exit /b 1
    git branch -M main || exit /b 1
)

git add . || exit /b 1

REM Skip the commit step cleanly if there's nothing to commit (re-runs).
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "feat: initial Quick Purchase Invoice app (Item-or-Account row toggle)" || exit /b 1
) else (
    echo Nothing new to commit.
)

REM Add remote only if it doesn't already exist.
git remote get-url origin >NUL 2>&1
if errorlevel 1 (
    git remote add origin https://github.com/Syncflo-design/quick_purchase_invoice.git || exit /b 1
)

git push -u origin main || exit /b 1

echo.
echo Done. View at https://github.com/Syncflo-design/quick_purchase_invoice
