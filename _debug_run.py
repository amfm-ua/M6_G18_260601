from src.engine.modelo.model import run_model
try:
    run_model(cenario='Base', hub_on=False, ecogres_on=False)
    print('OK')
except Exception as e:
    import traceback
    traceback.print_exc()
