"""GrestelModel — avaliação por DCF-FCFF, Múltiplos e FCFE.

Interface get_params / set_params / compute_synthesis compatível com
o Monte Carlo (monte_carlo.py).  Não altera o modelo operacional existente.
"""
from __future__ import annotations

from typing import Any


# Pesos por defeito: 50 % DCF-FCFF, 30 % Múltiplos, 20 % FCFE
_W_DCF = 0.50
_W_MULT = 0.30
_W_FCFE = 0.20


class GrestelModel:
    """Valuation model: DCF-FCFF + Múltiplos + FCFE → equity value ponderado.

    Parâmetros esperados (ver excel_reader.load_params para lista completa):
        WACC, ke, g_terminal, tax_rate, net_debt, shares,
        EBIT_base, DA_base, capex_base, delta_nwc_base, EBITDA_base,
        EV_EBITDA_sector, EV_EBIT_sector, PE_sector, PBV_sector, EV_Sales_sector,
        projected_FCFF  : dict[int, float] | None
        projected_FCFE  : dict[int, float] | None
        projected_revenue: dict[int, float] | None
    """

    def __init__(self, params: dict[str, Any]) -> None:
        self._params: dict[str, Any] = dict(params)

    # ── interface Monte Carlo ────────────────────────────────────────────────

    def get_params(self) -> dict[str, Any]:
        """Devolve cópia rasa dos parâmetros actuais."""
        return dict(self._params)

    def set_params(self, p: dict[str, Any]) -> None:
        """Actualiza parâmetros internos (merge; não substitui projecções se omitidas)."""
        self._params.update(p)

    def compute_synthesis(self) -> dict[str, float]:
        """Calcula equity value pelos três métodos e devolve síntese ponderada.

        Retorna
        -------
        dict com chaves:
            equity_dcf, equity_multiples, equity_fcfe,
            weighted_equity, min_price
        """
        p = self._params
        equity_dcf = self._equity_dcf(p)
        equity_mult = self._equity_multiples(p)
        equity_fcfe = self._equity_fcfe(p)

        w_dcf = float(p.get("w_dcf", _W_DCF))
        w_mult = float(p.get("w_multiples", _W_MULT))
        w_fcfe = float(p.get("w_fcfe", _W_FCFE))
        total_w = w_dcf + w_mult + w_fcfe or 1.0

        weighted = (w_dcf * equity_dcf + w_mult * equity_mult + w_fcfe * equity_fcfe) / total_w

        neg_disc = float(p.get("negotiation_discount", -0.10))
        shares = float(p.get("shares") or 1.0)
        min_price = (weighted / shares) * (1.0 + neg_disc)

        return {
            "equity_dcf": equity_dcf,
            "equity_multiples": equity_mult,
            "equity_fcfe": equity_fcfe,
            "weighted_equity": weighted,
            "min_price": min_price,
        }

    # ── DCF-FCFF ─────────────────────────────────────────────────────────────

    def _equity_dcf(self, p: dict) -> float:
        wacc = float(p["WACC"])
        g = float(p["g_terminal"])
        net_debt = float(p.get("net_debt") or 0.0)

        fcffs = self._get_fcffs(p)
        if not fcffs:
            return -net_debt

        n = len(fcffs)
        pv = sum(cf / (1.0 + wacc) ** t for t, cf in enumerate(fcffs, 1))

        # Valor terminal de Gordon-Growth: FCFFn*(1+g) / (WACC-g)
        if wacc > g:
            tv = fcffs[-1] * (1.0 + g) / (wacc - g)
            pv += tv / (1.0 + wacc) ** n

        return pv - net_debt

    def _get_fcffs(self, p: dict) -> list[float]:
        """FCFFs projetados — aplica choques estocásticos do MC se presentes."""
        rev_shock = float(p.get("g_revenue_shock") or 0.0)
        margin_shock = float(p.get("EBITDA_margin_shock") or 0.0)

        raw: dict | None = p.get("projected_FCFF")
        if raw:
            years = sorted(raw.keys())
            base = [float(raw[yr] or 0.0) for yr in years]

            if rev_shock == 0.0 and margin_shock == 0.0:
                return base

            rev_raw: dict = p.get("projected_revenue") or {}
            result: list[float] = []
            for t, (cf, yr) in enumerate(zip(base, years), 1):
                cf_s = cf * (1.0 + rev_shock) ** t
                if margin_shock != 0.0 and rev_raw:
                    cf_s += margin_shock * float(rev_raw.get(yr) or 0.0)
                result.append(cf_s)
            return result

        # Sem projeções explícitas: calcular a partir dos parâmetros base
        return self._project_fcffs(p)

    def _project_fcffs(self, p: dict) -> list[float]:
        n = int(p.get("n_years") or 5)
        g = float(p.get("g_phase1_avg") or 0.05)
        tax = float(p.get("tax_rate") or 0.245)
        ebit = float(p.get("EBIT_base") or 0.0)
        da = float(p.get("DA_base") or 0.0)
        capex = float(p.get("capex_base") or 0.0)
        dnwc = float(p.get("delta_nwc_base") or 0.0)
        rev_shock = float(p.get("g_revenue_shock") or 0.0)
        margin_shock = float(p.get("EBITDA_margin_shock") or 0.0)

        fcffs: list[float] = []
        for t in range(1, n + 1):
            factor = (1.0 + g + rev_shock) ** t
            ebit_t = ebit * factor * (1.0 + margin_shock)
            da_t = da * (1.0 + g) ** t
            capex_t = capex * (1.0 + g) ** t
            dnwc_t = dnwc * (1.0 + g) ** t
            nopat_t = ebit_t * (1.0 - tax)
            fcffs.append(nopat_t + da_t - capex_t - dnwc_t)
        return fcffs

    # ── Múltiplos ────────────────────────────────────────────────────────────

    def _equity_multiples(self, p: dict) -> float:
        ebitda = float(p.get("EBITDA_base") or 0.0)
        ebit = float(p.get("EBIT_base") or 0.0)
        tax = float(p.get("tax_rate") or 0.245)
        net_income = ebit * (1.0 - tax)
        book_eq = float(p.get("E_equity") or 0.0)
        net_debt = float(p.get("net_debt") or 0.0)

        # Receita: primeiro ano das projeções ou estimativa por margem
        rev_raw: dict = p.get("projected_revenue") or {}
        if rev_raw:
            revenue = float(rev_raw[min(rev_raw.keys())] or 0.0)
        else:
            revenue = (ebitda / 0.15) if ebitda else 0.0

        # EV_EBITDA pode ser perturbado pelo MC como "EV_EBITDA_mult"
        ev_ebitda = float(p.get("EV_EBITDA_mult") or p.get("EV_EBITDA_sector") or 0.0)
        ev_ebit = float(p.get("EV_EBIT_sector") or 0.0)
        ev_sales = float(p.get("EV_Sales_sector") or 0.0)
        pe = float(p.get("PE_sector") or 0.0)
        pbv = float(p.get("PBV_sector") or 0.0)

        equities: list[float] = []
        if ev_ebitda and ebitda:
            equities.append(ev_ebitda * ebitda - net_debt)
        if ev_ebit and ebit:
            equities.append(ev_ebit * ebit - net_debt)
        if ev_sales and revenue:
            equities.append(ev_sales * revenue - net_debt)
        if pe and net_income:
            equities.append(pe * net_income)
        if pbv and book_eq:
            equities.append(pbv * book_eq)

        return sum(equities) / len(equities) if equities else 0.0

    # ── FCFE ─────────────────────────────────────────────────────────────────

    def _equity_fcfe(self, p: dict) -> float:
        ke = float(p.get("ke") or 0.10)
        g = float(p.get("g_terminal") or 0.02)

        raw: dict | None = p.get("projected_FCFE")
        if raw:
            years = sorted(raw.keys())
            fcfes = [float(raw[yr] or 0.0) for yr in years]
        else:
            # Aproximação: FCFE ≈ FCFF − juro líquido de impostos sobre dívida
            fcffs = self._get_fcffs(p)
            kd = float(p.get("kd") or 0.04)
            debt = float(p.get("net_debt") or 0.0)
            tax = float(p.get("tax_rate") or 0.245)
            int_net = kd * debt * (1.0 - tax)
            fcfes = [cf - int_net for cf in fcffs]

        if not fcfes:
            return 0.0

        n = len(fcfes)
        pv = sum(cf / (1.0 + ke) ** t for t, cf in enumerate(fcfes, 1))

        if ke > g:
            tv = fcfes[-1] * (1.0 + g) / (ke - g)
            pv += tv / (1.0 + ke) ** n

        return pv
