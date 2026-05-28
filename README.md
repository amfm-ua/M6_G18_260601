## M6_G18_260601 

Motor de planeamento financeiro da Grestel · UC PEF 2025-26 · Grupo 18 · ISCA-UA

Cobre M3 (Planeamento Financeiro) e M6 (Plano de Negócios), expondo todos os outputs via API REST e interface web.

---

## Arranque rápido

**Windows (sem Python instalado):** executar `SETUP.bat` uma vez → `start.bat`

**Com Python instalado:**

```
pip install -r requirements.txt
python server.py
```

| URL | |
|---|---|
| `http://localhost:8000/` | Interface web |
| `http://localhost:8000/docs` | Swagger UI (lista completa de endpoints) |
| `http://localhost:8000/health` | Estado (`{"ok": true}`) |

---

## O que cobre

**Demonstrações anuais 2024–2029:** DR · Balanço · DFC · KPIs e rácios financeiros

**Mensais 2025:** vendas · DR · tesouraria · EOEP fiscal · FSE (14 rubricas) · pessoal · CMVMC

**Cenários:** Base · Upside · Downside · Stress · cenários customizados

**Hub Logístico M6:** VAL · TIR · Payback · FCF · tornado · Monte Carlo · DSCR · mapa de investimento · plano de financiamento OE4

**Outros:** rolling forecast mensal · Ecogres · exportação Excel · SMART tracker · enquadramento estratégico M6

---

## Documentação

| Ficheiro | Conteúdo |
|---|---|
| [guia_docentes.md](guia_docentes.md) | Outputs, endpoints, cenários, cobertura PEF, verificação rápida |
| [project_tree.md](project_tree.md) | Estrutura de ficheiros, fluxo de dados, suite de testes |
| [docs/](docs/) | Documentos de apoio à elaboração do relatório M6 |
