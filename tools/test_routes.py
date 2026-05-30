import sys
sys.path.insert(0, ".")
from src.api.routes.hub import get_hub_viabilidade_cenarios

r = get_hub_viabilidade_cenarios(irc_taxa=None, wacc=None)
print("OK -", list(r.keys()))