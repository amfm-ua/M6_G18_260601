"""Suite consolidada de testes do editor YAML.

Este ficheiro agrega todos os testes relevantes para CI:
- test_yaml_editor_api: endpoints CRUD da API
- test_irc_single_source: arquitetura de duas taxas IRC (design, não bug)
- test_yaml_loader: camada loader sem cache
- test_yaml_propagation: matriz de propagação
- test_yaml_regression: testes de regressão

Executar com: pytest tests/test_yaml_editor_propagation.py -v
"""

# Re-exportar todos os testes
from tests.debug.test_yaml_editor_api import *
from tests.debug.test_irc_single_source import *
from tests.debug.test_yaml_loader import *
from tests.debug.test_yaml_propagation import *
from tests.debug.test_yaml_regression import *
