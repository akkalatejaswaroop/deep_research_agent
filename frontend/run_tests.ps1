$nextProcess = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -PassThru -NoNewWindow
Write-Host "Waiting for Next.js to start..."
Start-Sleep -Seconds 15
Write-Host "Running Playwright tests..."
npx playwright test
$testExitCode = $LASTEXITCODE
Write-Host "Stopping Next.js..."
Stop-Process -Id $nextProcess.Id -Force
exit $testExitCode
