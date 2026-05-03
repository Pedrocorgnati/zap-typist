"""Testes unitários do TerminalWidget — cobre US-005 (4 cenários BDD)."""

from __future__ import annotations

import threading

from PySide6.QtCore import QCoreApplication

from zap_typist.ui.widgets.terminal_widget import (
    MAX_CHARS_PER_LINE,
    MAX_LINES,
    TRIM_TO_LINES,
    TRUNCATE_SUFFIX,
    TerminalWidget,
)

# ---------------------------------------------------------------------------
# Cenário [SUCCESS] — output exibido em tempo real
# ---------------------------------------------------------------------------


def test_append_line_basico_renderiza(qtbot):
    """[SUCCESS] append_line do main thread exibe a linha."""
    widget = TerminalWidget()
    qtbot.addWidget(widget)
    widget.append_line("hello world")
    qtbot.wait(50)
    assert "hello world" in widget.export_text()


def test_append_line_de_thread_nao_qt_e_thread_safe(qtbot):
    """[SUCCESS] append_line chamado de thread não-Qt é roteado via signal sem crash."""
    widget = TerminalWidget()
    qtbot.addWidget(widget)

    def worker():
        for i in range(50):
            widget.append_line(f"linha {i}")

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    # Processa o event loop até os signals chegarem ao slot
    qtbot.wait(200)
    QCoreApplication.processEvents()
    text = widget.export_text()
    assert "linha 0" in text
    assert "linha 49" in text


def test_auto_scroll_para_ultima_linha(qtbot):
    """[SUCCESS] cursor de texto vai para o final após append."""
    widget = TerminalWidget()
    qtbot.addWidget(widget)
    for i in range(20):
        widget.append_line(f"L{i}")
    qtbot.wait(50)
    cursor = widget.textCursor()
    assert cursor.atEnd(), "Cursor deveria estar no final do documento"


# ---------------------------------------------------------------------------
# Cenário [EDGE] — buffer rotation
# ---------------------------------------------------------------------------


def test_buffer_rotation_ao_atingir_limite(qtbot):
    """[EDGE] ao ultrapassar MAX_LINES, mantém apenas as últimas TRIM_TO_LINES."""
    widget = TerminalWidget()
    qtbot.addWidget(widget)
    # Inserção direta via _do_append (síncrona, evita esperar event loop 10k vezes)
    for i in range(MAX_LINES + 100):
        widget._do_append(f"L{i}")
    line_count = widget.line_count()
    # Qt mantém um bloco vazio terminal — daí o + 1
    assert line_count <= TRIM_TO_LINES + 1, f"line_count={line_count}"
    # As linhas mais antigas foram descartadas
    text = widget.export_text()
    assert "L0" not in text
    # As mais recentes permanecem
    assert f"L{MAX_LINES + 99}" in text


# ---------------------------------------------------------------------------
# Cenário [EDGE] — truncagem de linha longa
# ---------------------------------------------------------------------------


def test_linha_longa_e_truncada(qtbot):
    """[EDGE] linha > MAX_CHARS_PER_LINE é truncada com sufixo padronizado."""
    widget = TerminalWidget()
    qtbot.addWidget(widget)
    long_line = "x" * (MAX_CHARS_PER_LINE + 500)
    widget.append_line(long_line)
    qtbot.wait(50)
    text = widget.export_text()
    assert TRUNCATE_SUFFIX in text
    # A string original gigante NÃO está no documento
    assert long_line not in text


def test_linha_no_limite_exato_nao_e_truncada(qtbot):
    """[EDGE] linha com exatamente MAX_CHARS_PER_LINE chars passa intacta."""
    widget = TerminalWidget()
    qtbot.addWidget(widget)
    line = "y" * MAX_CHARS_PER_LINE
    widget.append_line(line)
    qtbot.wait(50)
    text = widget.export_text()
    assert TRUNCATE_SUFFIX not in text
    assert line in text


# ---------------------------------------------------------------------------
# Cenário [ERROR] — set_running reflete idle após exceção
# ---------------------------------------------------------------------------


def test_set_running_alterna_estado_visual(qtbot):
    """[ERROR/SUCCESS] set_running(True/False) altera stylesheet sem erros."""
    widget = TerminalWidget()
    qtbot.addWidget(widget)
    widget.set_running(True)
    assert "5b8def" in widget.styleSheet().lower()
    widget.set_running(False)
    assert "5b8def" not in widget.styleSheet().lower()


# ---------------------------------------------------------------------------
# Invariantes adicionais
# ---------------------------------------------------------------------------


def test_widget_e_read_only(qtbot):
    widget = TerminalWidget()
    qtbot.addWidget(widget)
    assert widget.isReadOnly() is True


def test_clear_esvazia_buffer(qtbot):
    widget = TerminalWidget()
    qtbot.addWidget(widget)
    widget.append_line("conteudo")
    qtbot.wait(50)
    widget.clear()
    assert widget.export_text() == ""


def test_line_count_reflete_appends(qtbot):
    """[CONTRACT C1] line_count() expõe a contagem sem acoplar ao QTextDocument."""
    widget = TerminalWidget()
    qtbot.addWidget(widget)
    assert widget.line_count() == 1  # bloco vazio inicial do Qt
    for i in range(5):
        widget.append_line(f"linha {i}")
    qtbot.wait(50)
    # Primeiro append preenche o bloco vazio inicial; demais criam novos blocos.
    assert widget.line_count() == 5
    widget.clear()
    assert widget.line_count() == 1
