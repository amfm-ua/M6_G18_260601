from src.engine.inputs.loader import load
from src.engine.operacional.pessoal import pessoal_anual
import pandas as pd

vn_df = pd.DataFrame([{"ano": y, "vn_total": 50_000_000 * (1.07 ** (y - 2024))} for y in range(2024, 2030)])

a, base, _ = load()
df_sem = pessoal_anual(a, base, vn_df)[["ano", "headcount", "gastos_pessoal"]]

a_hub, base2, _ = load()
a_hub.raw.setdefault("hub_logistico", {})["incluir_hub"] = True
df_com = pessoal_anual(a_hub, base2, vn_df)[["ano", "headcount", "gastos_pessoal"]]

merged = df_sem.merge(df_com, on="ano", suffixes=("_sem_hub", "_com_hub"))
merged["delta_hc"] = merged["headcount_com_hub"] - merged["headcount_sem_hub"]
print(merged.to_string(index=False))
