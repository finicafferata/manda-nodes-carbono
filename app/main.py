# --- PRIMERO: Importaciones ---
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing import Dict, Any, Optional, Literal
from .state import GraphState, TaskStateType
from .nodes.conversation import (
    start_node,
    process_company_name_node,
    process_responsible_name_node,
    process_employee_count_node,
    process_energy_expenses_light_node,
    process_energy_expenses_fuel_node,
    process_energy_expenses_gas_node,
    process_employee_transport_node,
)
from .persistence import save_data_node
from .llm_integration import configure_gemini_client
import traceback
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SEGUNDO: Definición de la función create_data_collection_workflow ---

def route_next_step(state: GraphState) -> Literal[
    "start_node",
    "process_company_name_node",
    "process_responsible_name_node",
    "process_employee_count_node",
    "process_energy_expenses_light_node",
    "process_energy_expenses_fuel_node",
    "process_energy_expenses_gas_node",
    "process_employee_transport_node",
    "save_data_node",
    "__end__"
]:
    """Decide qué nodo ejecutar basándose en la tarea actual."""
    task = state.current_task
    logger.info(f"Router: Tarea actual = {task}")

    if task is None:
        # Estado inicial, ir al nodo de bienvenida
        return "start_node"
    elif task == "esperando_nombre_empresa":
        return "process_company_name_node"
    elif task == "esperando_nombre_responsable":
        return "process_responsible_name_node"
    elif task == "esperando_cantidad_empleados":
        return "process_employee_count_node"
    elif task == "esperando_gasto_luz":
        return "process_energy_expenses_light_node"
    elif task == "esperando_gasto_combustible":
        return "process_energy_expenses_fuel_node"
    elif task == "esperando_gasto_gas":
        return "process_energy_expenses_gas_node"
    elif task == "esperando_transporte_empleados":
        return "process_employee_transport_node"
    elif task == "finalizando": # Tarea puesta por process_employee_transport_node
        return "save_data_node"
    else:
        # Estado inesperado, terminar el grafo
        logger.error(f"Router: Tarea inesperada encontrada: {task}. Finalizando.")
        return "__end__"


def create_data_collection_workflow() -> StateGraph:
    """Crea un grafo para la recolección de datos de la empresa, controlado por tareas."""
    workflow = StateGraph(GraphState)

    # --- 1. Añadir todos los nodos ---
    nodes_to_add = [
        ("start_node", start_node),
        ("process_company_name_node", process_company_name_node),
        ("process_responsible_name_node", process_responsible_name_node),
        ("process_employee_count_node", process_employee_count_node),
        ("process_energy_expenses_light_node", process_energy_expenses_light_node),
        ("process_energy_expenses_fuel_node", process_energy_expenses_fuel_node),
        ("process_energy_expenses_gas_node", process_energy_expenses_gas_node),
        ("process_employee_transport_node", process_employee_transport_node),
        ("save_data_node", save_data_node)
    ]
    for name, node_func in nodes_to_add:
        workflow.add_node(name, node_func)

    # Nodo para marcar fin (igual que antes)
    def mark_finished_node(state: GraphState) -> Dict[str, Any]:
        logger.info("--- Marcando conversación como finalizada ---")
        return {"conversation_finished": True}
    workflow.add_node("mark_finished_node", mark_finished_node)

    # --- 2. Definir el punto de entrada condicional ---
    workflow.set_conditional_entry_point(
        route_next_step,
        {
            "start_node": "start_node",
            "process_company_name_node": "process_company_name_node",
            "process_responsible_name_node": "process_responsible_name_node",
            "process_employee_count_node": "process_employee_count_node",
            "process_energy_expenses_light_node": "process_energy_expenses_light_node",
            "process_energy_expenses_fuel_node": "process_energy_expenses_fuel_node",
            "process_energy_expenses_gas_node": "process_energy_expenses_gas_node",
            "process_employee_transport_node": "process_employee_transport_node",
            "save_data_node": "save_data_node",
            "__end__": END
        }
    )

    # --- 3. Definir las transiciones DESPUÉS de cada nodo ---
    workflow.add_edge("start_node", END)
    workflow.add_edge("process_company_name_node", END)
    workflow.add_edge("process_responsible_name_node", END)
    workflow.add_edge("process_employee_count_node", END)
    workflow.add_edge("process_energy_expenses_light_node", END)
    workflow.add_edge("process_energy_expenses_fuel_node", END)
    workflow.add_edge("process_energy_expenses_gas_node", END)
    workflow.add_edge("process_employee_transport_node", END)
    workflow.add_edge("save_data_node", "mark_finished_node")
    workflow.add_edge("mark_finished_node", END)

    return workflow


# --- TERCERO: Definición de la función main (Sin cambios lógicos necesarios aquí) ---
def main():
    print("\n=== Iniciando Asistente de Recolección de Datos ===\n")
    try:
        configure_gemini_client()
    except Exception as e:
         # Salir si la configuración falla (ej. API key no encontrada por la librería)
         logger.error(f"Fallo al configurar el cliente LLM: {e}. Asegúrate que GOOGLE_API_KEY está configurada.")
         return

    workflow = create_data_collection_workflow()
    memory = MemorySaver() # Mantenemos por si se usa checkpointing
    try:
        app = workflow.compile(checkpointer=memory)
    except Exception as e:
        print(f"Error compilando grafo: {e}")
        traceback.print_exc()
        return

    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    print(f"ID Conversación: {thread_id}")

    current_state_obj = None
    try:
        # Invocación inicial sólo para ejecutar el router -> start_node -> END
        # El estado se actualizará con el mensaje de bienvenida y current_task="esperando_nombre_empresa"
        app.invoke({}, config)
        state_snapshot = app.get_state(config)
        if state_snapshot and state_snapshot.values:
             current_state_obj = GraphState.model_validate(state_snapshot.values)
             # logger.debug(f"Estado inicial: {current_state_obj}") # Para depuración
        else:
             logger.error("Estado inicial no recuperado después de la primera invocación.")
             return
    except Exception as e:
        logger.error(f"Error en la invocación inicial del grafo: {e}", exc_info=True)
        return

    # Bucle principal (igual que antes)
    last_printed_message_count = 0
    while current_state_obj and not getattr(current_state_obj, 'conversation_finished', False):
        # Mostrar mensajes
        if hasattr(current_state_obj, 'messages') and isinstance(current_state_obj.messages, list):
             new_message_count = len(current_state_obj.messages)
             if new_message_count > last_printed_message_count:
                 for i in range(last_printed_message_count, new_message_count):
                     if current_state_obj.messages[i]:
                         print("\nAsistente:", current_state_obj.messages[i], "\n")
                 last_printed_message_count = new_message_count

        # Obtener input
        user_input = ""
        try:
            user_input = input("Usuario: ").strip()
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("\nAsistente: Finalizando a petición del usuario.")
                final_state_dict = current_state_obj.model_dump()
                final_state_dict['current_task'] = 'finalizando'
                try:
                    # Intenta llamar directamente a la función, no al nodo del grafo
                    from .persistence import save_interaction_data
                    save_interaction_data(GraphState.model_validate(final_state_dict))
                except Exception as save_err:
                     logger.error(f"Error guardando datos al salir: {save_err}")
                break
        except KeyboardInterrupt:
            print("\n\nAsistente: Interrupción detectada. Finalizando.")
            final_state_dict = current_state_obj.model_dump()
            final_state_dict['current_task'] = 'finalizando'
            try:
                from .persistence import save_interaction_data
                save_interaction_data(GraphState.model_validate(final_state_dict))
            except Exception as save_err:
                 logger.error(f"Error guardando datos en interrupción: {save_err}")
            break
        except Exception as e:
            logger.error(f"Error durante la entrada del usuario: {e}")
            break

        # Invocar el grafo con la entrada
        input_for_invoke = {"user_input": user_input}
        try:
            # La ejecución comenzará con 'route_next_step' que dirigirá al nodo correcto
            app.invoke(input_for_invoke, config)
            state_snapshot = app.get_state(config)
            if state_snapshot and state_snapshot.values:
                 current_state_obj = GraphState.model_validate(state_snapshot.values)
                 # logger.debug(f"Estado actualizado: {current_state_obj}") # Para depuración
            else:
                logger.error("Estado no recuperado después de invoke. Terminando.")
                break
        except Exception as e:
            logger.error(f"Error durante la invocación del grafo: {e}", exc_info=True)
            break

        if getattr(current_state_obj, 'conversation_finished', False):
            logger.info("... (Conversación finalizada según el grafo) ...")

    # Mostrar últimos mensajes si los hubiera (igual que antes)
    if current_state_obj and hasattr(current_state_obj, 'messages') and isinstance(current_state_obj.messages, list):
         new_message_count = len(current_state_obj.messages)
         if new_message_count > last_printed_message_count:
             for i in range(last_printed_message_count, new_message_count):
                 if current_state_obj.messages[i]:
                     print("\nAsistente:", current_state_obj.messages[i], "\n")

    print("\n=== Fin de la conversación ===\n")


if __name__ == "__main__":
    main()