$bytes = [System.IO.File]::ReadAllBytes("E:\Job Search\Project Ideas\Luddy Hackathon\neural-compression-pipeline\service_ocr\entrypoint.sh")
$fixed = $bytes -replace ([char]13 -replace [char]10), ([char]10)
[System.IO.File]::WriteAllBytes("E:\Job Search\Project Ideas\Luddy Hackathon\neural-compression-pipeline\service_ocr\entrypoint.sh", $fixed)
Write-Host "Fixed line endings"