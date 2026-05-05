# Windows Server
Виконайте PowerShell як Адміністратор:
```powershell
iwr -Uri 'https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/scripts/deploy_windows_exporter.ps1' | iex
```
**Порт:** 9182

# Linux Server
Виконайте команду в терміналі:
```bash
curl -sSL https://raw.githubusercontent.com/ajjs1ajjs/Monitoring/main/scripts/deploy_node_exporter.sh | sudo bash
```
**Порт:** 9100
