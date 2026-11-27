# Перевірка API з PowerShell (сервер має бути запущений: python app.py)
# Запуск у ДРУГОМУ терміналі: powershell -ExecutionPolicy Bypass -File test_http.ps1

$base = "http://127.0.0.1:5000"
$ok = '{"date": "2026-11-23", "vehicle": "F/A-18C", "mode": "РБ", "result": "перемога", "kills": 4, "minutes": 12}'
$bad = '{"date": "2026-11-23", "vehicle": "F/A-18C", "mode": "РБ", "result": "перемога", "kills": "три", "minutes": 12}'

function Show($title, $cmd) {
    Write-Host "`n== $title" -ForegroundColor Cyan
    try {
        $r = & $cmd
        Write-Host $r.StatusCode
        Write-Host $r.Content
    } catch {
        Write-Host $_.Exception.Response.StatusCode.value__ -ForegroundColor Yellow
        Write-Host $_.ErrorDetails.Message
    }
}

$utf8 = [System.Text.Encoding]::UTF8
Show "POST добрий бій (201)"   { Invoke-WebRequest "$base/battles" -Method Post -ContentType "application/json; charset=utf-8" -Body $utf8.GetBytes($ok) }
Show "POST кривий бій (400)"   { Invoke-WebRequest "$base/battles" -Method Post -ContentType "application/json; charset=utf-8" -Body $utf8.GetBytes($bad) }
Show "POST без тіла (400)"     { Invoke-WebRequest "$base/battles" -Method Post }
Show "GET усі бої (200)"       { Invoke-WebRequest "$base/battles" }
Show "GET звіт (200)"          { Invoke-WebRequest "$base/report" }
Show "DELETE неіснуючий (404)" { Invoke-WebRequest "$base/battles/99999" -Method Delete }
