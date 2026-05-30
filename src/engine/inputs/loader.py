"""
Módulo: inputs/loader.py — Carregamento Agregado dos Dados do Modelo Financeiro Grestel
Versão: v2 — Estrutura modular temática
Idioma: Português Europeu

OBJETIVO ACADÉMICO:
Este módulo implementa o padrão de carregamento em camadas de dados financeiros.
Realiza:
  1. Leitura sequencial dos ficheiros YAML (bases de dados estruturadas);
  2. Agregação e normalização dos dados financeiros por ano civil;
  3. Aplicação de cenários (Base, Upside, Downside) através de overrides estruturados;
  4. Retorno de três estruturas consolidadas: Assumptions, Base2024, Schedules.

LÓGICA FINANCEIRA:
- Base Financeira: dados de referência (2024 real e projetos 2025-2029);
- Cenários: variações nas hipóteses de crescimento (volume, preço, custos);
  - Upside: cenário otimista (5% crescimento vendas em volume e preço);
  - Base: cenário central (sem variações);
  - Downside: cenário pessimista (crescimento moderado 1-2% em vendas).
- Subsidiárias: dados específicos da Ecogres e Hub Logístico (opcionais).

FLUXO:
  load() → carrega YAMLs → normaliza por ano → aplica cenário override → retorna estruturas
"""

from __future__ import annotations

from .custom_scenarios import load_custom_scenarios
from .models import Assumptions, Base2024, Schedules
from .paths import (
    ASSUMPTIONS_FILE,
    BASE2024_FILE,
    COZEDURA_FILE,
    CUSTOS_2025_FILE,
    CUSTOS_2026_2029_FILE,
    CUSTOS_2030_2034_FILE,
    ECOGRES_ASSUMPTIONS_FILE,
    HUB_ASSUMPTIONS_FILE,
    MACRO_2025_FILE,
    MACRO_2026_2029_FILE,
    MACRO_2030_2034_FILE,
    MERCADORIAS_FILE,
    MERCADORIAS_2024_FILE,
    MIX_2024_FILE,
    MIX_2025_FILE,
    PRODUTOS_FILE,
    PRODUTOS_2024_FILE,
    SCHEDULES_FILE,
    VENDAS_2025_FILE,
    VENDAS_2026_2029_FILE,
    VENDAS_2030_2034_FILE,
)
from .yaml_io import (
    _deep_update,
    _load_yaml_layers,
    _normalizar_chaves_ano,
    _normalizar_mercadorias,
    _yaml_load,
)


# OVERRIDES POR CENÁRIO: Variações aplicadas sobre o cenário Base
# Conceito: cada cenário modifica as hipóteses de crescimento (drivers) de forma coerente.
# Os overrides são mesclados com os dados base usando _deep_update (merge recursivo).
#
# NOTAÇÃO:
#   - "base_2025": refere-se ao período completo 2025 (12 meses)
#   - Anos 2026-2034: períodos completos (12 meses por ano)
#
# CENÁRIO UPSIDE (Otimista):
#   - Crescimento em volume de vendas: 5% a.a. em 2025-2028, +4% em 2029, +2.5% em 2030-2034
#   - Crescimento em preço de vendas: 5% a.a. em 2025-2026, moderando para 2% em 2030-2034
#   - Crescimento FSE: 4% em 2028-2029, +2% em 2030-2034
#
# CENÁRIO BASE (Central):
#   - Sem variações: mantém os dados como definidos nos YAML
#
# CENÁRIO DOWNSIDE (Pessimista):
#   - Crescimento em volume de vendas: 2% a.a. em 2025-2027, desacelerando a 0.5% em 2030-2034
#   - Crescimento em preço de vendas: apenas 1% a.a. (pressure de concorrência)
#   - Crescimento FSE: 4% em 2025-2027, acelerando a 3% em 2030-2034
#
# ---------------------------------------------------------------------------
# Overrides de cenário — SPREADS REAIS (Filosofia B)
#
# Os valores abaixo são spreads reais acima da inflação.
# O engine compõe a inflação em runtime: nominal = (1+inf)×(1+real)−1
#
# Volume é grandeza física — valores directos (não compostos com inflação).
#
# Conversão de referência (nominal → real):
#   real = (1+nominal)/(1+inflação) − 1
#   com inflações: 2025≈2.2%, 2026=2.0%, 2027=1.8%, 2028=1.7%, 2029=1.6%, 2030-2034=1.5%
# ---------------------------------------------------------------------------
_SCENARIO_OVERRIDES: dict[str, dict] = {
    "Base": {},
    "Upside": {
        # Volume: directo (grandeza física)
        "crescimento_volume_vendas": {
            "base_2025": 0.05,
            2026: 0.05,
            2027: 0.05,
            2028: 0.05,
            2029: 0.04,
            2030: 0.025,
            2031: 0.025,
            2032: 0.025,
            2033: 0.025,
            2034: 0.025,
        },
        # PVU: spreads reais
        "crescimento_pvu_vendas": {
            "base_2025": 0.027,
            2026: 0.029,
            2027: 0.022,
            2028: 0.023,
            2029: 0.014,
            2030: 0.020,
            2031: 0.020,
            2032: 0.020,
            2033: 0.020,
            2034: 0.020,
        },
        # FSE: spread real
        "crescimento_fse": {
            2028: 0.023,
            2029: 0.024,
            2030: 0.010,
            2031: 0.010,
            2032: 0.010,
            2033: 0.010,
            2034: 0.010,
        },
        # Diferenciação geográfica e de canal — cenário optimista
        # NOTA: estes diferenciais aplicam-se apenas a 2025; 2026-2034 usam crescimento_volume_vendas global
        "crescimento_volume_por_mercado": {"PT": 0.00, "UE": 0.03, "USA": 0.03, "ROW": 0.01},
        "crescimento_volume_por_canal": {"Private_Label": 0.02, "Hotelaria": 0.05, "Retalho": 0.01, "E_Commerce": 0.04},
        "crescimento_pvu_por_mercado": {"PT": 0.01, "UE": 0.01, "USA": 0.03, "ROW": 0.00},
        "crescimento_pvu_por_canal": {"Private_Label": 0.00, "Hotelaria": 0.02, "Retalho": 0.00, "E_Commerce": 0.015},
    },
    "Downside": {
        # Volume: directo
        "crescimento_volume_vendas": {
            "base_2025": 0.02,
            2026: 0.02,
            2027: 0.02,
            2028: 0.01,
            2029: 0.01,
            2030: 0.005,
            2031: 0.005,
            2032: 0.005,
            2033: 0.005,
            2034: 0.005,
        },
        # PVU: spread real negativo — preço não acompanha inflação
        "crescimento_pvu_vendas": {
            "base_2025": -0.012,
            2026: -0.010,
            2027: -0.008,
            2028: -0.007,
            2029: -0.006,
            2030: -0.003,
            2031: -0.003,
            2032: -0.003,
            2033: -0.003,
            2034: -0.003,
        },
        # FSE: spread real positivo — custos sobem acima da inflação
        "crescimento_fse": {
            "base_2025": 0.018,
            2026: 0.020,
            2027: 0.022,
            2028: 0.042,
            2029: 0.043,
            2030: 0.025,
            2031: 0.025,
            2032: 0.025,
            2033: 0.025,
            2034: 0.025,
        },
        # Diferenciação geográfica e de canal — cenário pessimista
        # NOTA: diferenciais aplicam-se apenas a 2025; 2026-2034 usam crescimento_volume_vendas global
        "crescimento_volume_por_mercado": {"PT": 0.00, "UE": -0.02, "USA": -0.03, "ROW": -0.01},
        "crescimento_volume_por_canal": {"Private_Label": -0.03, "Hotelaria": -0.03, "Retalho": -0.01, "E_Commerce": 0.01},
        "crescimento_pvu_por_mercado": {"PT": 0.00, "UE": -0.01, "USA": -0.03, "ROW": -0.01},
        "crescimento_pvu_por_canal": {"Private_Label": -0.02, "Hotelaria": 0.00, "Retalho": -0.01, "E_Commerce": 0.00},
        # Hub Logístico — haircuts para ambiente adverso
        "hub_logistico": {
            "projeto_hub": {
                "beneficios_anuais": {
                    "poupanca_operacional": 408000,    # 480 000 × 0.85
                    "opex_incremental":     182000,    # 132 000 manutenção/SLA + 50 000 técnico IA
                    "beneficio_liquido_anual": 306000, # 408k + 80k − 182k
                },
            },
        },
    },
    "Hub_Ativo": {
        # DR consolidada com todos os impactos do hub (poupança pessoal/FSE/CMVMC + PT2030)
        "hub_logistico": {
            "incluir_hub": True,
        },
    },
    "Stress": {
        # Floor económico: o PVU não cai abaixo do custo industrial (CIP). Sob
        # stress os preços comprimem-se até ao custo e param aí — a partir desse
        # ponto o choque manifesta-se em perda de volume, não em venda abaixo do
        # custo. Sem isto, vários produtos vendiam abaixo do CIP em 2025.
        "pvu_floor_at_cup": True,
        # Volume: directo (contracção real)
        "crescimento_volume_vendas": {
            "base_2025": -0.02,
            2026: 0.00,
            2027: 0.01,
            2028: 0.02,
            2029: 0.02,
        },
        # PVU: spread real muito negativo — incapacidade de repercutir inflação
        "crescimento_pvu_vendas": {
            "base_2025": -0.022,
            2026: -0.010,
            2027: -0.008,
            2028: -0.007,
            2029:  0.004,
        },
        # FSE: spread real elevado — choque energético acima da inflação geral
        "crescimento_fse": {
            "base_2025": 0.037,
            2026: 0.029,
            2027: 0.031,
            2028: 0.042,
            2029: 0.043,
        },
        # Pessoal: pressão salarial acima da inflação
        "crescimento_pessoal": {
            "base_2025": 0.027,
            2026: 0.029,
            2027: 0.022,
            2028: 0.023,
            2029: 0.033,
        },
        # Diferenciação geográfica e de canal — cenário de stress
        # USA: choque tarifário severo (tarifas agressivas inviabilizam margens actuais)
        # ROW: contágio geopolítico e desaceleração global
        # UE: contágio económico, cautela nos mercados europeus
        # Hotelaria: colapso da hotelaria (crises no turismo + cancelamento de grandes contratos)
        # Private_Label: paragem súbita de encomendas (excess stock de produto acabado)
        # PVU USA: absorção tarifária + incapacidade de repercutir preços ao mercado
        # PVU Hotelaria: descontos agressivos para reter os contratos remanescentes
        # NOTA: estes diferenciais aplicam-se apenas a 2025; 2026-2029 usam crescimento_volume_vendas global
        "crescimento_volume_por_mercado": {"PT": -0.01, "UE": -0.03, "USA": -0.12, "ROW": -0.05},
        "crescimento_volume_por_canal": {"Private_Label": -0.05, "Hotelaria": -0.10, "Retalho": -0.02, "E_Commerce": -0.02},
        "crescimento_pvu_por_mercado": {"PT": -0.01, "UE": -0.02, "USA": -0.08, "ROW": -0.04},
        "crescimento_pvu_por_canal": {"Private_Label": -0.03, "Hotelaria": -0.05, "Retalho": -0.01, "E_Commerce": -0.01},
        # Hub Logístico — haircuts severos + atraso de ramp-up
        # poupança −30%: choque energético nos fornos eleva OPEX automação;
        #   qualidade de pasta instável limita ganhos de IA/visão picking;
        #   upskilling mais lento em ambiente de crise (Academia Grestel)
        # ramp_up_por_ano: apenas 60 % dos benefícios capturados no ano 1 (2026),
        #   atingindo plena maturação no ano 3 (2028)
        "hub_logistico": {
            "projeto_hub": {
                "beneficios_anuais": {
                    "poupanca_operacional":    336000,  # 480 000 × 0.70 (−30 %)
                    "reducao_quebras":          21000,  # re-ancorado custo de conversão perdido (base 85k × haircut stress)
                    "opex_incremental":        200000,  # 150 000 manutenção/SLA + 50 000 técnico IA (custo fixo)
                    "beneficio_liquido_anual": 157000,  # 336k + 21k − 200k
                    "ramp_up_por_ano": {
                        2026: 0.60,   # 1.º ano operacional: 60 % capturado
                        2027: 0.80,   # 2.º ano: curva aprendizagem ~80 %
                        2028: 1.00,   # plena maturação
                        2029: 1.00,
                    },
                },
            },
        },
    },
    "OE5": {
        "impostos": {
            "IRC_taxa_geral": 0.21,
            "Derrama_Estadual": 0.04,
            "RFAI_limite_pct_coleta": 0.30,
        },
        "macro": {
            "inflacao_geral": 0.030,
        },
    },
    "Tarifa_EUA": {
        "mercados": {
            "USA": {
                "tarifa_impacto": 0.25,
            },
        },
    },
}

# Recalibracao M6 do Hub Logistico.
#
# Mantem os cenarios do projeto alinhados com o YAML base atual:
#   Base: poupanca 440k, quebras 85k (custo de conversão perdido), OPEX 225k, inventario via dias de DMI.
# A camada abaixo tambem evita que overrides historicos deixem o Downside
# artificialmente melhor do que o Base.
_HUB_SCENARIO_RECALIBRATION: dict[str, dict] = {
    "Upside": {
        "hub_logistico": {
            "projeto_hub": {
                "beneficios_anuais": {
                    "poupanca_operacional": 484000,
                    "reducao_quebras": 98000,
                    "opex_incremental": 210000,
                    "beneficio_liquido_anual": 372000,
                    "crescimento_anual": 0.040,
                },
                # Inventário via dias de DMI (Upside: automação no topo da janela VDMA)
                "inventario_dmi": {"clearing_dias": 30.0},
                "dmi_reducao_hub": {"DMI_PA_reducao_dias": 15, "DMI_MP_reducao_dias": 12},
                "beneficios_comerciais": {
                    "vn_incremental": {
                        2026: 450000,
                        2027: 750000,
                        2028: 1000000,
                        2029: 1150000,
                        2030: 1200000,
                        2031: 1260000,
                        2032: 1320000,
                        2033: 1390000,
                        2034: 1460000,
                    },
                    "cmvmc_pct_incremental": 0.52,
                },
                "necessidades_fundo_maneio": {
                    "compras_manutencao_anuais": 84000,
                    "receita_servicos_externos": {
                        2026: 0, 2027: 220000, 2028: 340000, 2029: 400000,
                        2030: 440000, 2031: 490000, 2032: 540000, 2033: 600000, 2034: 660000,
                    },
                },
                "viabilidade": {"wacc": 0.069},  # Base 7,3 % − 0,4 pp (Upside)
            },
        },
    },
    "Downside": {
        "hub_logistico": {
            "projeto_hub": {
                "beneficios_anuais": {
                    "poupanca_operacional": 374000,
                    "reducao_quebras": 59500,
                    "opex_incremental": 247500,
                    "beneficio_liquido_anual": 186000,
                    "crescimento_anual": 0.025,
                    "ramp_up_por_ano": {
                        2026: 0.75,
                        2027: 0.90,
                        2028: 1.00,
                        2029: 1.00,
                    },
                },
                # Inventário via dias de DMI (Downside: automação aquém do plano)
                "inventario_dmi": {"clearing_dias": 16.0},
                "dmi_reducao_hub": {"DMI_PA_reducao_dias": 9, "DMI_MP_reducao_dias": 6},
                "beneficios_comerciais": {
                    "vn_incremental": {
                        2026: 250000,
                        2027: 450000,
                        2028: 600000,
                        2029: 675000,
                        2030: 700000,
                        2031: 735000,
                        2032: 772000,
                        2033: 810000,
                        2034: 851000,
                    },
                    "cmvmc_pct_incremental": 0.60,
                },
                "necessidades_fundo_maneio": {
                    "compras_manutencao_anuais": 99000,
                    "receita_servicos_externos": {
                        2026: 0, 2027: 140000, 2028: 210000, 2029: 250000,
                        2030: 270000, 2031: 295000, 2032: 320000, 2033: 350000, 2034: 385000,
                    },
                },
                "viabilidade": {"wacc": 0.081},  # Base 7,3 % + 0,8 pp (Downside)
            },
        },
    },
    "Stress": {
        "hub_logistico": {
            "projeto_hub": {
                "beneficios_anuais": {
                    "poupanca_operacional": 308000,
                    "reducao_quebras": 25500,
                    "opex_incremental": 281250,
                    "beneficio_liquido_anual": 52250,
                    "crescimento_anual": 0.015,
                    "ramp_up_por_ano": {
                        2026: 0.60,
                        2027: 0.80,
                        2028: 1.00,
                        2029: 1.00,
                    },
                },
                # Inventário via dias de DMI (Stress: ganhos estruturais mínimos)
                "inventario_dmi": {"clearing_dias": 10.0},
                "dmi_reducao_hub": {"DMI_PA_reducao_dias": 7, "DMI_MP_reducao_dias": 4},
                "beneficios_comerciais": {
                    "vn_incremental": {
                        2026: 150000,
                        2027: 250000,
                        2028: 350000,
                        2029: 400000,
                        2030: 420000,
                        2031: 441000,
                        2032: 463000,
                        2033: 486000,
                        2034: 510000,
                    },
                    "cmvmc_pct_incremental": 0.65,
                },
                "necessidades_fundo_maneio": {
                    "compras_manutencao_anuais": 112500,
                    "receita_servicos_externos": {
                        2026: 0, 2027: 80000, 2028: 120000, 2029: 140000,
                        2030: 150000, 2031: 165000, 2032: 180000, 2033: 198000, 2034: 218000,
                    },
                },
                "viabilidade": {"wacc": 0.091},  # Base 7,3 % + 1,8 pp (Stress)
            },
        },
    },
}

for _scenario_name, _hub_override in _HUB_SCENARIO_RECALIBRATION.items():
    _SCENARIO_OVERRIDES[_scenario_name] = _deep_update(
        _SCENARIO_OVERRIDES.get(_scenario_name, {}),
        _hub_override,
    )

CENARIOS = list(_SCENARIO_OVERRIDES.keys())


def load(cenario: str = "Base"):
    """
    Função Principal: Carrega e consolida os dados financeiros do modelo.

    PARÂMETRO:
      cenario (str): Um de {'Base', 'Upside', 'Downside'}. Define qual conjunto de
                     variações de crescimento aplicar sobre os dados base.

    RETORNA:
      tuple[Assumptions, Base2024, Schedules]: Três estruturas principais:
        1. Assumptions: hipóteses operacionais e financeiras (2025-2029, + cenário);
        2. Base2024: dados reais de 2024 (ponto de partida para projeções);
        3. Schedules: calendários plurianuais de valores (juros, depreciação, etc.).

    FLUXO INTERNO:

    PASSO 1: Carregamento e mesclagem de pressupostos (9 YAML em camadas)
      - MACRO_2025_FILE: inflação e câmbio EUR/USD — granularidade mensal 2025
      - MACRO_2026_2029_FILE: inflação e câmbio EUR/USD — granularidade anual 2026-2029
      - VENDAS_2025_FILE: pressupostos de vendas 2025
      - VENDAS_2026_2029_FILE: pressupostos de vendas 2026-2029
      - CUSTOS_2025_FILE: pressupostos de custos 2025
      - CUSTOS_2026_2029_FILE: pressupostos de custos 2026-2029
      - MIX_2024_FILE: mix real 2024 (base histórica de mercado/canal)
      - MIX_2025_FILE: mix planeamento 2025 (actualizado mensalmente)
      - ASSUMPTIONS_FILE: globais — fiscal, prazos, pessoal, ESG, sazonalidade
      → Resultado: dicionário consolidado de hipóteses

    PASSO 2: Carregamento de catálogos (opcionais)
      - PRODUTOS_FILE: lista e características de produtos (margem, cost, etc.)
      - MERCADORIAS_FILE: arquivo de mercadorias com estrutura de margem progressiva
      → Resultado: dois dicionários para lookup durante cálculos

    PASSO 3: Carregamento de dados base 2024
      - BASE2024_FILE: saldos iniciais de contas (caixa, crédito clientes, fornecedores)
      - SCHEDULES_FILE: tabelas plurianuais pré-calculadas (plano de financiamento,
                       calendário de depreciação, calendário de juros, etc.)
      → Resultado: dados "às linhas" de base para consolidação

    PASSO 4: Carregamento de subsidiárias (opcionais)
      - Ecogres: pressupostos específicos de Ecogres (se ativa)
      - Hub Logístico: pressupostos específicos do Hub M6 (se ativo)
      → Resultado: dados mesclados em assumptions["ecogres"] e assumptions["hub_logistico"]

    PASSO 5: Aplicação do cenário
      - Busca os overrides de crescimento em _SCENARIO_OVERRIDES[cenario]
      - Mescla recursivamente (crescimento volume/preço vendas, FSE)
      → Resultado: assumptions finalizadas com cenário aplicado

    PASSO 6: Retorno das três estruturas
      - Assumptions com flag cenario (p/ rastreabilidade)
      - Base2024 com referência aos produtos/mercadorias
      - Schedules para acesso a valores plurianuais pré-calculados
    """
    _custom = load_custom_scenarios().get("scenarios", {})
    if cenario not in _SCENARIO_OVERRIDES and cenario not in _custom:
        all_opts = list(_SCENARIO_OVERRIDES) + list(_custom)
        raise ValueError(f"Cenário '{cenario}' inválido. Opções: {all_opts}")

    # PASSO 1: Mesclagem em camadas de ficheiros de pressupostos
    # _load_yaml_layers aplica merge sucessivo (primeira sobrescreve, última ganha)
    assumptions = _normalizar_chaves_ano(
        _load_yaml_layers([
            MACRO_2025_FILE,                  # Macro 2025 — inflação/câmbio mensal
            MACRO_2026_2029_FILE,             # Macro 2026-2029 — inflação/câmbio anual
            MACRO_2030_2034_FILE,             # Macro 2030-2034 — inflação/câmbio anual
            VENDAS_2025_FILE,                 # Pressupostos vendas 2025
            VENDAS_2026_2029_FILE,            # Pressupostos vendas 2026-2029
            VENDAS_2030_2034_FILE,           # Pressupostos vendas 2030-2034
            CUSTOS_2025_FILE,                 # Pressupostos custos 2025
            CUSTOS_2026_2029_FILE,            # Pressupostos custos 2026-2029
            CUSTOS_2030_2034_FILE,            # Pressupostos custos 2030-2034
            MIX_2024_FILE,                    # Mix real 2024 (base histórica — única fonte de mix)
            ASSUMPTIONS_FILE,                 # Globais — fiscal, prazos, pessoal, ESG
        ])
    )

    # PASSO 2: Carregamento de catálogos (merge master + histórico 2024)
    produtos_master = _yaml_load(PRODUTOS_FILE, required=False) or {}
    produtos_2024   = _yaml_load(PRODUTOS_2024_FILE, required=False) or {}
    produtos = _normalizar_chaves_ano(_deep_update(produtos_master, produtos_2024))

    mercadorias_master = _yaml_load(MERCADORIAS_FILE, required=False) or {}
    mercadorias_2024   = _yaml_load(MERCADORIAS_2024_FILE, required=False) or {}
    mercadorias = _normalizar_mercadorias(
        _normalizar_chaves_ano(_deep_update(mercadorias_master, mercadorias_2024))
    )

    # PASSO 3: Base 2024 e Schedules
    base2024 = _normalizar_chaves_ano(_yaml_load(BASE2024_FILE))
    schedules = _normalizar_chaves_ano(_yaml_load(SCHEDULES_FILE))

    # PASSO 4: Carregamento de subsidiárias (opcionais, merge se presentes)
    ecogres_data = _normalizar_chaves_ano(
        _yaml_load(ECOGRES_ASSUMPTIONS_FILE, required=False)
    )
    hub_data = _normalizar_chaves_ano(
        _yaml_load(HUB_ASSUMPTIONS_FILE, required=False)
    )

    if ecogres_data:
        assumptions.setdefault("ecogres", ecogres_data)
    if hub_data:
        assumptions.setdefault("hub_logistico", hub_data)

    # Cenário "Cozedura de Baixa Temperatura" (toggle cozedura_on) — pressupostos
    # de eficiência térmica baseados na tese UA/Roca. A flag `incluir` é definida
    # em runtime por run_model(cozedura_on=...).
    cozedura_data = _yaml_load(COZEDURA_FILE, required=False) or {}
    coz_block = cozedura_data.get("cozedura_baixa_temp", cozedura_data)
    if coz_block:
        assumptions.setdefault("cozedura_baixa_temp", coz_block)

    # PASSO 5: Aplicação do cenário (override de crescimentos ou parâmetros custom)
    if cenario in _SCENARIO_OVERRIDES:
        overrides = _SCENARIO_OVERRIDES[cenario]
    else:
        overrides = _custom.get(cenario, {}).get("overrides", {})
    if overrides:
        assumptions = _deep_update(assumptions, overrides)

    # PASSO 6: Retorno das três estruturas consolidadas
    return (
        Assumptions(
            assumptions,
            cenario=cenario,
            produtos_raw=produtos,
            mercadorias_raw=mercadorias,
        ),
        Base2024(
            base2024,
            produtos_raw=produtos,
            mercadorias_raw=mercadorias,
        ),
        Schedules(schedules),
    )
