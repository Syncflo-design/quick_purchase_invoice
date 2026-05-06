@echo off
REM Robust update-and-push for quick_purchase_invoice.
REM Handles: stale .git/index.lock, half-staged index from prior bash runs,
REM "nothing to commit" when files are actually changed, etc.

cd /d C:\ClaudeCode\CoWork_Helper\projects\quick_purchase_invoice || exit /b 1

echo === Cleaning any stale git locks ===
if exist .git\index.lock (
    echo Removing stale .git\index.lock
    del /q .git\index.lock
)

echo.
echo === Repo status before push ===
git status --short

echo.
echo === Resetting index to HEAD (drops any half-staged work from prior runs) ===
git reset HEAD >NUL 2>&1

echo.
echo === Staging all changes ===
git add -A

echo.
echo === What's about to be committed ===
git status --short

echo.
echo === Committing ===
git diff --cached --quiet
if errorlevel 1 (
    git commit -m "fix(assets): rename CSS to qpi_styles.css to bypass CDN cache; v0.0.4" || (echo COMMIT FAILED & exit /b 1)
) else (
    echo Nothing staged to commit. Working tree may already match origin.
)

echo.
echo === Pushing to origin/main ===
git push origin main
if errorlevel 1 (
    echo PUSH FAILED. Possible causes:
    echo   - GitHub credentials expired - re-authenticate via the credential popup
    echo   - Branch is behind origin - run: git pull --rebase origin main
    exit /b 1
)

echo.
echo === Done ===
echo View at https://github.com/Syncflo-design/quick_purchase_invoice
git log --oneline -5
pause
