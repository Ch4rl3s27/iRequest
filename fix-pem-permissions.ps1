# Fix .pem permissions so SSH accepts the key (run in PowerShell)
$pem = "C:\Users\Abel\Desktop\iRequest\irequest.pem"
if (-not (Test-Path $pem)) {
    Write-Host "File not found: $pem"
    exit 1
}
# Remove inheritance and all existing permissions
icacls $pem /inheritance:r
icacls $pem /grant:r "$($env:USERNAME):(R)"
Write-Host "Done. Try: ssh -i `"$pem`" ubuntu@44.223.68.230"
