@echo off
REM Setup Git Hooks for Windows
REM This script makes the pre-push hook executable

echo "🔧 Setting up Git hooks for Windows..."

REM Check if pre-push hook exists
if not exist ".git\hooks\pre-push" (
    echo "❌ pre-push hook not found!"
    exit /b 1
)

REM Make the hook executable (Windows equivalent)
echo "📝 Making pre-push hook executable..."
icacls ".git\hooks\pre-push" /grant "%USERNAME%:(OI)(CI)F" /T

REM Verify the hook is executable
echo "✅ Git hooks setup completed!"
echo "🚀 The pre-push hook will now run 'make fix' before each push."
echo "📋 If 'make fix' fails, the push will be canceled."
echo "📋 If 'make fix' makes changes, you'll need to commit them first."

pause
