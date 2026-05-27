import sys
sys.path.insert(0, 'src')
from src.engine.modelo.model import run_model
from src.engine.projetos.hub_logistico import load as hub_load, hub_dr_impact, pt2030_reconhecimento, hub_nfm

# --- 1. Verificar double-counting PT2030 no DR ---
hub = hub_load()
subsidio_real = pt2030_reconhecimento(hub)
print("=== PT2030 reconhecimento real (uma vez) ===")
for y, v in sorted(subsidio_real.items()):
    print(f"  {y}: {v:,.0f}")

dfs = run_model(cenario='Base', hub_on=True, ecogres_on=False)
dr = dfs['dr']
print("\n=== DR: outros_rend e hub_outros_rend_subsidio ===")
for _, r in dr.iterrows():
    print(f"  {int(r['ano'])}: outros_rend={r['outros_rend']:,.0f}  hub_sub={r.get('hub_outros_rend_subsidio',0):,.0f}")

# --- 2. Verificar double-counting inventário na DFC ---
dfc = dfs['dfc']
bal = dfs['balanco']
print("\n=== Inventários no Balanço ===")
for _, r in bal.iterrows():
    print(f"  {int(r['ano'])}: inventarios={r['inventarios']:,.0f}")

print("\n=== DFC var_nfm e hub_nfm ===")
for _, r in dfc.iterrows():
    if r['ano'] >= 2025:
        print(f"  {int(r['ano'])}: var_nfm={r['var_nfm']:,.0f}  hub_nfm={r.get('hub_nfm',0):,.0f}")

# --- 3. Reconciliação DFC ---
print("\n=== DFC reconciliacao_ok ===")
for _, r in dfc.iterrows():
    if r['ano'] >= 2025:
        rok = r.get('reconciliacao_ok', 'N/A')
        print(f"  {int(r['ano'])}: caixa_fim={r.get('caixa_fim',0):,.0f}  caixa_balanco={r.get('caixa_fim_balanco',0):,.0f}  ok={rok}")

# --- 4. Comparar hub ativo vs inativo: efeito no outros_rend ---
dfs_off = run_model(cenario='Base', hub_on=False, ecogres_on=False)
dr_off = dfs_off['dr']
print("\n=== outros_rend: sem hub vs com hub (diferença) ===")
for y in [2025, 2026, 2027, 2028, 2029]:
    on_val = float(dr[dr.ano == y]['outros_rend'].iloc[0])
    off_val = float(dr_off[dr_off.ano == y]['outros_rend'].iloc[0])
    sub_real = subsidio_real.get(y, 0)
    diff = on_val - off_val
    print(f"  {y}: sem={off_val:,.0f}  com={on_val:,.0f}  diff={diff:,.0f}  PT2030_real={sub_real:,.0f}")
