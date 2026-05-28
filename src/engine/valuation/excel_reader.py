"""Leitor de pressupostos a partir do ficheiro Excel OE05_G18_260601.xlsx.

Usa openpyxl com data_only=True para obter valores calculados (não fórmulas).
A função load_params() devolve um dict com exactamente as mesmas chaves que
GrestelModel espera, permitindo passagem directa: GrestelModel(load_params(path)).
"""
from __future__ import annotations

import os
from typing import Any

import openpyxl

# ── Nomes das folhas ─────────────────────────────────────────────────────────
_SHEET_PARAMS = "⚙️ Pressupostos"
_SHEET_DCF = "📊 DCF-FCFF"
_SHEET_FCFE = "💰 FCFE"
_SHEET_SYNTHESIS = "🏆 Síntese"

# Colunas e anos do período explícito (anos 1–5)
_YEAR_COLS = ["C", "D", "E", "F", "G"]
_YEAR_KEYS = [2025, 2026, 2027, 2028, 2029]

# Path por defeito: ficheiro na raiz do projecto
_DEFAULT_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "OE05_G18_260601.xlsx"
)


def load_params(filepath: str | None = None) -> dict[str, Any]:
    """Lê todos os inputs do Excel e devolve dict compatível com GrestelModel.

    Parâmetros
    ----------
    filepath : str | None
        Caminho para o ficheiro xlsx.  Se None usa _DEFAULT_PATH.

    Retorna
    -------
    dict com chaves escalares + chaves de projecção (projected_*: dict[int, float]).

    Levanta
    -------
    FileNotFoundError se o ficheiro não existir.
    KeyError se uma folha obrigatória não existir.
    """
    path = os.path.normpath(filepath or _DEFAULT_PATH)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Ficheiro Excel não encontrado: {path}")

    wb = openpyxl.load_workbook(path, data_only=True)

    try:
        ps = wb[_SHEET_PARAMS]
        dcf = wb[_SHEET_DCF]
        fcfe_sheet = wb[_SHEET_FCFE]
        syn = wb[_SHEET_SYNTHESIS]
    except KeyError as exc:
        wb.close()
        raise KeyError(f"Folha não encontrada no Excel: {exc}") from exc

    params: dict[str, Any] = {}

    # ── Pressupostos (inputs manuais e células calculadas) ───────────────────
    cell_map: dict[str, str] = {
        "base_year": "C8",
        "n_years": "C10",
        "rf": "C12",
        "erp": "C13",
        "beta": "C14",
        "ke": "C15",          # CAPM calculado
        "tax_rate": "C16",
        "kd_gross": "C17",
        "kd": "C18",          # kd_gross*(1-tax_rate)
        "D": "C19",
        "E_equity": "C20",
        "wd": "C21",          # D/(D+E)
        "we": "C22",          # E/(D+E)
        "WACC": "C23",        # ke*we + kd*wd
        "g_phase1_avg": "C25",
        "g_phase2_avg": "C26",
        "g_terminal": "C27",
        "reinv_rate": "C28",  # g_terminal/ROC
        "ROC": "C29",
        "EBIT_base": "C31",
        "DA_base": "C32",
        "capex_base": "C33",
        "delta_nwc_base": "C34",
        "EBITDA_base": "C35",  # EBIT_base + DA_base
        "net_debt": "C36",
        "shares": "C37",
        "EV_EBITDA_sector": "C39",
        "EV_EBIT_sector": "C40",
        "PE_sector": "C41",
        "PBV_sector": "C42",
        "EV_Sales_sector": "C43",
    }
    for key, cell in cell_map.items():
        params[key] = _cell_value(ps[cell])

    # ── Projecções anuais DCF-FCFF ───────────────────────────────────────────
    dcf_rows: dict[str, int] = {
        "revenue": 9,
        "EBITDA": 11,
        "DA": 13,
        "EBIT": 14,
        "NOPAT": 17,
        "DA_dcf": 20,
        "capex": 21,
        "delta_nwc": 22,
        "FCFF": 23,
    }
    for metric, row in dcf_rows.items():
        params[f"projected_{metric}"] = {
            yr: _cell_value(dcf[f"{col}{row}"])
            for col, yr in zip(_YEAR_COLS, _YEAR_KEYS)
        }

    # ── Projecções anuais FCFE ───────────────────────────────────────────────
    fcfe_rows: dict[str, int] = {
        "NI": 9,
        "capex_liq": 10,
        "delta_nwc_fcfe": 11,
        "new_debt_net": 12,
        "FCFE": 13,
    }
    for metric, row in fcfe_rows.items():
        params[f"projected_{metric}"] = {
            yr: _cell_value(fcfe_sheet[f"{col}{row}"])
            for col, yr in zip(_YEAR_COLS, _YEAR_KEYS)
        }

    # ── Síntese ──────────────────────────────────────────────────────────────
    synthesis_map: dict[str, str] = {
        "equity_dcf": "C4",
        "equity_multiples": "C5",
        "equity_fcfe": "C6",
        "weighted_equity": "C7",
        "negotiation_discount": "C11",
        "min_price": "C12",
    }
    for key, cell in synthesis_map.items():
        params[key] = _cell_value(syn[cell])

    wb.close()
    return params


# ── Utilitário ───────────────────────────────────────────────────────────────

def _cell_value(cell: Any) -> Any:
    """Devolve o valor da célula, convertendo None para 0.0 em células numéricas."""
    v = cell.value
    # Manter strings e None tal qual; conversão de tipos numéricos é feita no modelo
    return v
