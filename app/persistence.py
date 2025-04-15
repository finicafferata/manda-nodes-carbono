import json
import datetime
from typing import Dict, Any
from .state import GraphState # Ya no necesitamos LoanOption aquí
import logging

logger = logging.getLogger(__name__)
LOG_FILE = "interactions_log.json" # Mantenemos el mismo archivo de log

def save_interaction_data(state: GraphState) -> bool:
    """Guarda los datos de la empresa recolectados durante la interacción."""
    # Crear el registro con los campos relevantes del NUEVO GraphState
    interaction_record = {
        "interaction_id": getattr(state, 'interaction_id', 'N/A'),
        "timestamp": datetime.datetime.now().isoformat(),

        # --- Campos Nuevos de Empresa ---
        "company_name": getattr(state, 'company_name', None),
        "responsible_name": getattr(state, 'responsible_name', None),
        "employee_count": getattr(state, 'employee_count', None),
        "expense_light": getattr(state, 'expense_light', None),
        "expense_fuel": getattr(state, 'expense_fuel', None),
        "expense_gas": getattr(state, 'expense_gas', None),
        "employee_transport_method": getattr(state, 'employee_transport_method', None),

        # --- Campos Antiguos (Eliminados) ---
        # "requested_amount": getattr(state, 'requested_amount', None),
        # "credit_type_purpose": getattr(state, 'credit_type_purpose', None),
        # "monthly_income": getattr(state, 'monthly_income', None),
        # "monthly_expenses": getattr(state, 'monthly_expenses', None),
        # "cashflow_description": getattr(state, 'cashflow_description', None),
        # "preference": getattr(state, 'preference', None),
        # "is_unaffordable": getattr(state, 'is_unaffordable', None),
        # "presented_option": ...,
        # "calculation_error_occurred": ...,

        # Podríamos guardar el historial de mensajes si es útil
        # "messages_history": getattr(state, 'messages', [])
    }
    try:
        # Lógica para leer, añadir y escribir en el JSON (sin cambios)
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f: log_data = json.load(f)
            if not isinstance(log_data, list): log_data = []
        except (FileNotFoundError, json.JSONDecodeError): log_data = []

        log_data.append(interaction_record)

        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            # Usar default=str para manejar tipos no serializables (aunque ahora son más simples)
            json.dump(log_data, f, indent=4, ensure_ascii=False, default=str)
        logger.info(f"Datos de interacción {interaction_record['interaction_id']} guardados en {LOG_FILE}.")
        return True
    except Exception as e:
        logger.error(f"Error guardando interacción {interaction_record.get('interaction_id', 'N/A')}: {e}", exc_info=True)
        return False

def save_data_node(state: GraphState) -> Dict[str, Any]:
    """Nodo que llama a la función de persistencia."""
    logger.info("--- Guardando Datos de Interacción ---")
    success = save_interaction_data(state)
    # Este nodo ahora es llamado justo antes de 'mark_finished_node',
    # así que no necesita devolver un 'current_task'.
    # Devolver un diccionario vacío o con alguna info de éxito/fallo es suficiente.
    return {"persistence_success": success}