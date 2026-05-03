# NOTICE — Atribuições de Software de Terceiros

**Projeto:** Zap Typist
**Gerado em:** 2026-05-03

Este projeto utiliza os seguintes componentes de software de terceiros:

---

## Licenças Permissivas (MIT, BSD, Apache, PSF)

| Pacote | Versão | Licença | Uso |
|--------|--------|---------|-----|
| SQLAlchemy | 2.0.49 | MIT | produção |
| pydantic | 2.13.3 | MIT | produção |
| pydantic-core | 2.46.3 | MIT | produção (transitiva) |
| pydantic-settings | 2.14.0 | MIT | produção |
| python-dotenv | 1.2.2 | BSD-3-Clause | produção |
| annotated-types | 0.7.0 | MIT | produção (transitiva) |
| exceptiongroup | 1.3.1 | MIT | produção (transitiva) |
| greenlet | 3.5.0 | MIT AND Python-2.0 | produção (transitiva, SQLAlchemy async) |
| typing-extensions | 4.15.0 | PSF-2.0 | produção (transitiva) |
| typing-inspection | 0.4.2 | MIT | produção (transitiva) |
| pytest | 9.0.3 | MIT | dev/test |
| pytest-cov | 7.1.0 | MIT | dev/test |
| pytest-qt | 4.5.0 | MIT | dev/test |
| ruff | 0.15.12 | MIT | dev |
| mypy | 1.20.2 | MIT | dev |
| mypy-extensions | 1.1.0 | MIT | dev (transitiva) |
| factory-boy | 3.3.3 | MIT | dev/test |
| faker | 40.15.0 | MIT | dev/test (transitiva) |
| deptry | 0.25.1 | MIT | dev |
| click | 8.3.3 | BSD License | dev (transitiva) |
| requirements-parser | 0.13.0 | Apache Software License | dev (transitiva) |
| coverage | 7.13.5 | Apache-2.0 | dev/test (transitiva) |
| pluggy | 1.6.0 | MIT | dev/test (transitiva) |
| iniconfig | 2.3.0 | MIT | dev/test (transitiva) |
| tomli | 2.4.1 | MIT | dev/test (transitiva) |
| pygments | 2.20.0 | BSD License | dev/test (transitiva) |
| librt | 0.9.0 | MIT | dev (transitiva) |

---

## Licenças LGPL/MPL (Copyleft Fraco)

| Pacote | Versão | Licença | Observação |
|--------|--------|---------|------------|
| PySide6 | 6.11.0 | LGPL-3.0 + Qt Commercial | Modificações à biblioteca PySide6 devem ser abertas; linkagem dinâmica (padrão) é permitida em projetos proprietários |
| PySide6-Addons | 6.11.0 | LGPL-3.0 + Qt Commercial | Idem |
| PySide6-Essentials | 6.11.0 | LGPL-3.0 + Qt Commercial | Idem |
| shiboken6 | 6.11.0 | LGPL-3.0 + Qt Commercial | Idem |
| pathspec | 1.1.1 | MPL 2.0 | Modificações ao pathspec devem ser abertas; uso em aplicação proprietária é permitido |
| hypothesis | 6.152.4 | MPL 2.0 | Dev/test only; MPL compatível com uso em projetos proprietários |

**Nota LGPL (PySide6):** A distribuição de aplicações que usam PySide6 sob LGPL requer que o usuário final possa substituir os componentes PySide6 por versões modificadas. Em distribuição via `pip install` isso é satisfeito automaticamente. Vide: https://www.qt.io/qt-licensing

**Nota MPL (pathspec, hypothesis):** A Mozilla Public License 2.0 permite uso em projetos proprietários. Modificações nos próprios arquivos MPL devem ser divulgadas sob MPL, mas o código da aplicação proprietária não precisa ser aberto.

---

**AGPL:** Nenhum pacote AGPL detectado.
**GPL (copyleft forte):** Nenhum pacote GPL detectado.
**Licenças proprietárias/desconhecidas:** Nenhuma nas dependências do projeto.

---

*Gerado automaticamente por /dependency-audit. Revisar antes de distribuição pública.*
