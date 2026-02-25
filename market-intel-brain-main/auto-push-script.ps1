# PowerShell script for auto-pushing to GitHub
# This will be called after each commit

param(
    [string]$Branch = "main"
)

Write-Host "🚀 Auto-pushing to GitHub..." -ForegroundColor Green

try {
    # Push to origin
    $result = git push origin $Branch
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Pushed to GitHub successfully!" -ForegroundColor Green
    } else {
        Write-Host "❌ Push failed!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Error pushing to GitHub: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
