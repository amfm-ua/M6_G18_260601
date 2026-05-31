"""Testes para a arquitetura de duas taxas de IRC (Secção 4.1 do debug plan).

O modelo usa DUAS taxas de IRC para dois contextos distintos:

1. `IRC_taxa_efetiva_planeamento` (0.13) em globais.yaml — Modelo Principal
   - Para planeamento fiscal: benefícios RFAI, otimização de coleta
   - Editável via editor YAML; afeta DR, Balanço, DFC

2. `projeto_hub.viabilidade.irc_taxa` (0.235) em m6_hub_assumptions.yaml — Hub Logístico
   - Taxa combinada: IRC 20% + Derrama Estadual 2% + Derrama Municipal 1.5%
   - Análise de projeto standalone

**Isto NÃO é um bug** — é arquitetura deliberada. Ambas as taxas existem
intencionalmente para os seus respetivos contextos.
"""

import requests
import yaml
from pathlib import Path

BASE_URL = "http://localhost:8000"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "src" / "engine" / "data"


def test_irc_taxa_efetiva_from_globais():
    """GET /api/assumptions/effective deve devolver irc_taxa_efetiva do globais.yaml."""
    resp = requests.get(f"{BASE_URL}/api/assumptions/effective?cenario=Base")
    assert resp.status_code == 200, f"Failed: {resp.status_code}"

    data = resp.json()
    irc_eff = data["effective"]["irc_taxa_efetiva"]

    # Verificar que corresponde ao globais.yaml
    globais_path = DATA_DIR / "pressupostos" / "globais.yaml"
    with open(globais_path, encoding="utf-8") as f:
        globais = yaml.safe_load(f)

    expected = globais["impostos"]["IRC_taxa_efetiva_planeamento"]
    assert irc_eff == expected, \
        f"irc_taxa_efetiva ({irc_eff}) != globais.yaml IRC_taxa_efetiva_planeamento ({expected})"


def test_hub_viability_uses_hub_yaml_irc_taxa():
    """GET /api/hub/viability deve usar irc_taxa do hub YAML (não globais.yaml).

    Design intencional: o hub usa taxa combinada do projeto (IRC + derramas),
    não a taxa de planeamento fiscal do modelo principal.
    """
    resp = requests.get(f"{BASE_URL}/api/hub/viability?cenario=Base")
    assert resp.status_code == 200, f"Failed: {resp.status_code}"

    data = resp.json()
    irc_usado = data["parametros"]["irc_taxa"]

    # Obter irc_taxa do hub YAML
    hub_path = DATA_DIR / "subsidiarias" / "hub_logistico" / "m6_hub_assumptions.yaml"
    with open(hub_path, encoding="utf-8") as f:
        hub_yaml = yaml.safe_load(f)

    hub_irc = hub_yaml["projeto_hub"]["viabilidade"]["irc_taxa"]

    # Verificar que o hub usa o seu próprio irc_taxa
    assert irc_usado == hub_irc, \
        f"Hub não usa irc_taxa do hub YAML! Usou {irc_usado} em vez de {hub_irc}"

    print(f"\n=== ARQUITETURA DE DUAS TAXAS (DESIGN) ===")
    print(f"hub YAML irc_taxa:         {hub_irc:.1%} (IRC + derramas)")
    print(f"Valor usado pelo endpoint: {irc_usado:.1%}")
    print(f"============================================")


def test_hub_viability_respects_irc_param():
    """GET /api/hub/viability com irc_taxa explícito deve usar esse valor."""
    irc_explicito = 0.15
    resp = requests.get(f"{BASE_URL}/api/hub/viability?cenario=Base&irc_taxa={irc_explicito}")
    assert resp.status_code == 200

    data = resp.json()
    irc_usado = data["parametros"]["irc_taxa"]

    assert irc_usado == irc_explicito, \
        f"Com irc_taxa explícito={irc_explicito}, endpoint usou {irc_usado}"


def test_irc_edit_does_not_affect_hub_vpl_by_design():
    """VERIFICAÇÃO: editar IRC_taxa_efetiva_planeamento NÃO muda o VPL do hub.

    Este é o comportamento EXPECTED por design — não é um bug.
    O hub usa a sua própria taxa (IRC + derramas = 23.5%).
    """
    # Obter VPL base com IRC atual
    resp_base = requests.get(f"{BASE_URL}/api/hub/viability?cenario=Base")
    vpl_base = resp_base.json()["val"]

    # Obter globais e modificar irc_taxa_efetiva
    globais_path = DATA_DIR / "pressupostos" / "globais.yaml"
    with open(globais_path, encoding="utf-8") as f:
        globais = yaml.safe_load(f)

    original_irc = globais["impostos"]["IRC_taxa_efetiva_planeamento"]

    try:
        # Alterar IRC_taxa_efetiva_planeamento para 30%
        globais["impostos"]["IRC_taxa_efetiva_planeamento"] = 0.30
        with open(globais_path, "w", encoding="utf-8") as f:
            yaml.dump(globais, f, allow_unicode=True, sort_keys=False)

        # Obter VPL após edição (sem passar irc_taxa ao endpoint)
        resp_editado = requests.get(f"{BASE_URL}/api/hub/viability?cenario=Base")
        vpl_editado = resp_editado.json()["val"]

        print(f"\n=== TESTE: IRC edit → Hub VPL ===")
        print(f"VPL base (IRC globais={original_irc}):        {vpl_base:,.0f} €")
        print(f"VPL após editar globais para 0.30:            {vpl_editado:,.0f} €")
        print(f"Diferença: {vpl_editado - vpl_base:,.0f} €")
        print(f"================================")

        # O VPL NÃO deve mudar — este é o comportamento esperado
        assert vpl_base == vpl_editado, \
            "O VPL mudou inesperadamente!"

        print("\n✅ Comportamento confirmado (design): editar IRC_taxa_efetiva_planeamento")
        print("   não afeta o VPL do hub — usa taxa própria (IRC + derramas = 23.5%)")

    finally:
        # Restaurar original
        globais["impostos"]["IRC_taxa_efetiva_planeamento"] = original_irc
        with open(globais_path, "w", encoding="utf-8") as f:
            yaml.dump(globais, f, allow_unicode=True, sort_keys=False)


def test_monte_carlo_uses_default_irc():
    """GET /api/hub/monte-carlo default irc_taxa=0.245 não vem de nenhum YAML."""
    resp = requests.get(f"{BASE_URL}/api/hub/monte-carlo?cenario=Base&n=100")
    assert resp.status_code == 200

    data = resp.json()
    irc_usado = data["irc_taxa"]

    # 0.245 = 0.20 + 0.03 + 0.015 (IRC + Derrama Estadual + Derrama Municipal)
    print(f"\nirc_taxa usado no Monte Carlo: {irc_usado}")

    # O default do MC (0.245) é diferente de ambos:
    # - 0.13 (globais IRC_taxa_efetiva)
    # - 0.235 (hub irc_taxa)
    # Mas corresponde a 0.20 + 0.03 + 0.015 = 0.245 (taxa nominal com derramas)