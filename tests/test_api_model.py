import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / 'src'))

from src.engine.modelo.model import dataframe_to_records, run_model


def test_run_model_returns_expected_outputs():
    dfs = run_model("Base", hub_on=False, ecogres_on=False)
    rec = dataframe_to_records(dfs)

    for key in ("dr", "balanco", "dfc", "kpis"):
        assert key in dfs
        assert key in rec

    assert "fse_detalhe_anual" in dfs
    assert "fse_detalhe_mensal_2025" in dfs
    assert len(dfs["fse_detalhe_anual"]) > 0
    assert sum(sum(v.values()) for v in dfs["fse_detalhe_mensal_2025"].values()) > 0


def test_vendas_mercado_anual_reconcilia_e_reage_a_crescimento_ue():
    dfs = run_model("Base", hub_on=False, ecogres_on=False)
    rec = dataframe_to_records(dfs)

    mercados_2025 = [r for r in rec["vendas_mercado_anual"] if r["ano"] == 2025]
    dr_2025 = next(r for r in rec["dr"] if r["ano"] == 2025)

    assert abs(sum(r["vn"] for r in mercados_2025) - dr_2025["vn"]) < 0.01

    base_ue = next(r["peso"] for r in mercados_2025 if r["mercado"] == "UE")
    dfs_ue = run_model(
        "Base",
        hub_on=False,
        ecogres_on=False,
        assumptions_overrides={
            "crescimento_volume_por_mercado": {
                "PT": 0.0,
                "UE": 0.50,
                "USA": 0.0,
                "ROW": 0.0,
            },
        },
    )
    rec_ue = dataframe_to_records(dfs_ue)
    mercados_ue_2025 = [r for r in rec_ue["vendas_mercado_anual"] if r["ano"] == 2025]
    boosted_ue = next(r["peso"] for r in mercados_ue_2025 if r["mercado"] == "UE")

    assert boosted_ue > base_ue


def test_acrescimos_mensais_alteram_distribuicao_mensal_de_vendas():
    base = dataframe_to_records(
        run_model(
            "Base",
            assumptions_overrides={
                "crescimento_volume_vendas": {
                    "base_2025": 0.02,
                    "acrescimos_mensais": {"Mai": 0.0},
                },
            },
        )
    )
    bump = dataframe_to_records(
        run_model(
            "Base",
            assumptions_overrides={
                "crescimento_volume_vendas": {
                    "base_2025": 0.02,
                    "acrescimos_mensais": {"Mai": 0.01},
                },
            },
        )
    )

    def by_month(records):
        rows = records["vendas_mensal_2025"]
        return {
            mes: sum(r["vn"] for r in rows if r["mes"] == mes)
            for mes in ("Abr", "Mai", "Jun")
        }

    base_m = by_month(base)
    bump_m = by_month(bump)

    assert bump_m["Mai"] / base_m["Mai"] > bump_m["Abr"] / base_m["Abr"]
    assert bump_m["Mai"] / base_m["Mai"] > bump_m["Jun"] / base_m["Jun"]

