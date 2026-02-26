# Run this on your PC to commit and push the student dashboard update.
# Then run the pull + restart steps on the server (see DEPLOY_UPDATE.md).

Set-Location $PSScriptRoot

git add app/templates/student_dashboard.html
git status

$confirm = Read-Host "Commit and push these changes? (y/n)"
if ($confirm -eq 'y') {
    git commit -m "Remove dark mode from student dashboard"
    git push origin main
    Write-Host "Done. Now SSH to 44.223.68.230, run: cd to app folder, git pull, then restart the app."
} else {
    Write-Host "Cancelled."
}
