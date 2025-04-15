import json
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Definición de la estructura (sin cambios)
class ProductRule(Dict):
    product_id: str
    credit_type: Optional[str] 
    min_amount: float
    max_amount: float
    annual_rate: float
    num_installments: int

# Datos por defecto (sin cambios)
MANDALLOW_RULES_DATA: List[ProductRule] = [
    {"product_id": "MICRO_12", "credit_type": "microcredito", "min_amount": 500.0, "max_amount": 4999.99, "annual_rate": 0.95, "num_installments": 12},
    {"product_id": "CONSUMO_12", "credit_type": "consumo", "min_amount": 5000.0, "max_amount": 25000.0, "annual_rate": 0.85, "num_installments": 12},
    {"product_id": "CONSUMO_24", "credit_type": "consumo", "min_amount": 10000.0, "max_amount": 50000.0, "annual_rate": 0.88, "num_installments": 24}
    # Añadir regla prendaria para probar filtro:
    # {"product_id": "PRENDARIO_36", "credit_type": "prendario", "min_amount": 30000.0, "max_amount": 150000.0, "annual_rate": 0.78, "num_installments": 36}
]

RULES_FILE = "mandaflow_rules.json" 

def _save_default_rules():
    logger.info(f"Guardando reglas en {RULES_FILE}")
    try:
        with open(RULES_FILE, 'w', encoding='utf-8') as f:
            json.dump(MANDALLOW_RULES_DATA, f, indent=4, ensure_ascii=False)
    except IOError as e:
        logger.error(f"Error al guardar reglas: {e}")

# --- FUNCIÓN MODIFICADA (Sprint 10 - HU 35) ---
def load_mandaflow_rules(credit_type_filter: Optional[str] = None) -> List[ProductRule]:
    """
    Carga las reglas de productos, opcionalmente filtradas por tipo.
    """
    all_rules: List[ProductRule] = []
    try:
        with open(RULES_FILE, 'r', encoding='utf-8') as f:
            rules_from_file = json.load(f)
            if isinstance(rules_from_file, list) and all(isinstance(item, dict) and 'product_id' in item for item in rules_from_file):
                 all_rules = rules_from_file
                 # logger.debug(f"Reglas cargadas desde {RULES_FILE}") # Menos verboso
            else:
                 logger.warning(f"Formato inválido {RULES_FILE}. Usando/Guardando defecto.")
                 _save_default_rules(); all_rules = MANDALLOW_RULES_DATA
    except (FileNotFoundError, json.JSONDecodeError):
        logger.warning(f"{RULES_FILE} no encontrado/inválido. Usando/Guardando defecto.")
        _save_default_rules(); all_rules = MANDALLOW_RULES_DATA
    except IOError as e:
         logger.error(f"Error IO leyendo {RULES_FILE}: {e}. Usando defecto."); all_rules = MANDALLOW_RULES_DATA
    except Exception as e:
        logger.error(f"Error inesperado cargando reglas: {e}", exc_info=True); all_rules = MANDALLOW_RULES_DATA

    # --- Filtrado por Tipo de Crédito ---
    if credit_type_filter and credit_type_filter != "otro" and all_rules:
        # Normalizar filtro y tipos en reglas para comparación insensible a mayúsculas
        filter_lower = credit_type_filter.lower()
        filtered_rules = [
            rule for rule in all_rules 
            if rule.get("credit_type") and isinstance(rule.get("credit_type"), str) and rule.get("credit_type").lower() == filter_lower
        ]
        logger.info(f"Filtrando por tipo '{filter_lower}'. {len(filtered_rules)}/{len(all_rules)} reglas coinciden.")
        # Devolver vacío si el filtro no encontró nada
        if not filtered_rules:
            logger.warning(f"No se encontraron reglas para el tipo de crédito: {credit_type_filter}")
            return [] 
        return filtered_rules
    else:
        # logger.info("No se aplica filtro de tipo o se pidió 'otro'. Devolviendo todas las reglas.")
        return all_rules # Devolver todas si no hay filtro o es 'otro'

# Bloque de prueba actualizado
if __name__ == "__main__":
    print("--- Probando carga SIN filtro ---")
    rules_all = load_mandaflow_rules()
    print(json.dumps(rules_all, indent=2))

    print("\n--- Probando carga CON filtro 'consumo' ---")
    rules_consumo = load_mandaflow_rules(credit_type_filter="consumo")
    print(json.dumps(rules_consumo, indent=2))
    
    print("\n--- Probando carga CON filtro 'prendario' (debería dar vacío si no está en datos) ---")
    rules_prendario = load_mandaflow_rules(credit_type_filter="prendario")
    print(json.dumps(rules_prendario, indent=2))

    print("\n--- Probando carga CON filtro 'otro' (debería devolver todas) ---")
    rules_otro = load_mandaflow_rules(credit_type_filter="otro")
    print(f"Reglas devueltas para 'otro': {len(rules_otro)}")