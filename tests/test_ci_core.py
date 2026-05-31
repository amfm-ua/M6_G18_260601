"""Suite de testes CI Core — validação lógica, contabilística e financeira.

Este ficheiro agrega os testes essenciais para CI:
- test_invariantes_financeiras: Balanço fecha, DFC reconcilia com caixa
- test_rolling_articulacao: DR ↔ Balanço ↔ DFC articulam
- test_balanco_rt_regression: Reservas legais, RT formula
- test_kpis_contract: KPIs batem entre si
- test_covenants: Covenants bancários
- test_hub_viabilidade_cenarios: VPL/TIR do Hub por cenário
- test_viabilidade_primitivas: NPV/IRR matemático
- test_cozedura_smoke: Appraisal da Cozedura
- test_mensais_reconciliacao: Mensais fecham com DR anual

Executar com: pytest tests/test_ci_core.py -v
"""

# Re-exportar todos os testes
from tests.test_invariantes_financeiras import *
from tests.test_rolling_articulacao import *
from tests.test_balanco_rt_regression import *
from tests.test_kpis_contract import *
from tests.test_covenants import *
from tests.test_hub_viabilidade_cenarios import *
from tests.test_viabilidade_primitivas import *
from tests.test_cozedura_smoke import *
from tests.test_mensais_reconciliacao import *
from tests.test_api_reconcil import *