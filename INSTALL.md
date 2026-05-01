# Instalação — Zap Typist

Pré-requisitos para rodar em Ubuntu 22.04 X11.

## Dependências de sistema (apt)

```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3-pip \
  libxcb-cursor0 libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 \
  libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-shape0 \
  libxcb-sync1 libxcb-xfixes0 libxcb-xinerama0 libxcb-xkb1 \
  wmctrl xdotool google-chrome-stable
```

## Ambiente Python

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## Playwright (Chromium)

Necessário para o Rock 3 (envio via WhatsApp Web). O Playwright não está no `requirements.txt` — instalar separadamente:

```bash
playwright install chromium
```

## Validação

```bash
python -m zap_typist
```

Deve abrir uma janela com 4 abas e barra de status "DB pronto, 0 leads".

## Troubleshooting

- Sessão Wayland: o app exibe warning. Recomenda-se logar em sessão "Ubuntu on Xorg".
- Permissões `~/.local/share/zap-typist`: o app cria com `0700`. Se a pasta existir com perms diferentes, ajustar com `chmod 700 ~/.local/share/zap-typist`.
- Chrome não encontrado: instalar `google-chrome-stable` via apt ou definir `ZAP_TYPIST_CHROME_BIN` no `.env`.
- Erro Qt `xcb`: instalar as libs `libxcb-*` listadas acima e garantir sessão X11 (não Wayland).
