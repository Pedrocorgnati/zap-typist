# Estimativa de Custos — zap-typist

> App desktop local — sem cloud, sem servidor, sem hosting pago.

## Resumo

| Recurso | Custo Mensal | Notas |
|---------|-------------|-------|
| Compute | $0 | Maquina pessoal do Pedro (Ubuntu 22.04 LTS) |
| Banco de dados | $0 | SQLite local em `~/.local/share/zap-typist/zap_typist.db` |
| Storage | $0 | Filesystem local (0700) |
| CDN / Egress | $0 | Sem trafego de rede no skeleton |
| Logs | $0 | RotatingFileHandler local (10MB x 5 = max 50MB em disco) |
| CI/CD | $0 | Sem pipeline remoto (pre-commit local) |
| **Total** | **$0/mes** | |

## Custos Futuros Possiveis

| Cenario | Custo Estimado |
|---------|---------------|
| Chrome (Rock 3) — instalado via snap/apt | Gratis |
| Playwright + browsers | Gratis (pip install playwright + chromium) |
| wmctrl, xdotool (Rock 3, reparenting X11) | Gratis (apt) |
| Storage de backup GPG (`~/backups/`) | Depende do storage externo escolhido (USB, Dropbox, etc.) |

## Notas Operacionais

- **Disco**: DB cresce ~1KB por lead. Para 10.000 leads: ~10MB. Absolutamente gerenciavel.
- **Memoria**: PySide6 + Python ocupa ~80-150MB RSS em idle. Worker em execucao: +50MB peak.
- **CPU**: Idle: negligivel. Worker de query/mensagens: picos curtos. Rock 3 (Playwright): CPU
  depende do comportamento do Chrome — nao e problema em uso pessoal moderado.
- **Logs**: rotacao automatica 10MB x 5 = teto de ~50MB em disco para logs.

<!-- Gerado por /infra-create em 2026-05-01 -->
