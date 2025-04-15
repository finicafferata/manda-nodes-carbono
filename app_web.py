import streamlit as st
import os
import json
from datetime import datetime
import logging
import uuid

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar componentes necesarios del chatbot
from app.state import GraphState
from app.llm_integration import configure_gemini_client, call_gemini
from app.nodes.conversation import (
    process_company_name_node,
    process_responsible_name_node,
    process_employee_count_node,
    process_electricity_consumption_node,
    process_fuel_type_node,
    process_fuel_consumption_node,
    process_gas_consumption_node,
    process_commute_distance_node,
    process_car_percentage_node,
    process_public_transport_percentage_node,
    process_green_transport_percentage_node,
    process_waste_amount_node,
    process_recycle_percentage_node,
    process_water_consumption_node,
    process_paper_consumption_node,
    process_office_area_node,
    process_climate_control_node,
    process_air_travel_node,
    process_ground_travel_node,
    calculate_carbon_footprint_node
)

# Archivo para guardar las interacciones
LOG_FILE = "interactions_log.json"

# Inicializar la aplicación
st.set_page_config(page_title="Calculadora de Huella de Carbono", page_icon="🌍")
st.title("Calculadora de Huella de Carbono Empresarial")

# Función para guardar datos (adaptada de persistence.py)
def save_interaction_data(state):
    interaction_record = {
        "interaction_id": getattr(state, 'interaction_id', str(uuid.uuid4())),
        "timestamp": datetime.now().isoformat(),
        "company_name": getattr(state, 'company_name', None),
        "responsible_name": getattr(state, 'responsible_name', None),
        "employee_count": getattr(state, 'employee_count', None),
        "electricity_kwh": getattr(state, 'electricity_kwh', None),
        "fuel_type": getattr(state, 'fuel_type', None),
        "fuel_consumption": getattr(state, 'fuel_consumption', None),
        "gas_consumption": getattr(state, 'gas_consumption', None),
        "employee_commute_distance": getattr(state, 'employee_commute_distance', None),
        "transport_pct_car": getattr(state, 'transport_pct_car', None),
        "transport_pct_public": getattr(state, 'transport_pct_public', None),
        "transport_pct_green": getattr(state, 'transport_pct_green', None),
        "waste_kg": getattr(state, 'waste_kg', None),
        "recycle_pct": getattr(state, 'recycle_pct', None),
        "water_consumption": getattr(state, 'water_consumption', None),
        "paper_consumption": getattr(state, 'paper_consumption', None),
        "office_sqm": getattr(state, 'office_sqm', None),
        "climate_control": getattr(state, 'climate_control', None),
        "air_travel_km": getattr(state, 'air_travel_km', None),
        "ground_travel_km": getattr(state, 'ground_travel_km', None),
        "carbon_footprint": getattr(state, 'carbon_footprint', None),
        "carbon_per_employee": getattr(state, 'carbon_per_employee', None),
        "sustainability_score": getattr(state, 'sustainability_score', None)
    }
    
    try:
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f: 
                log_data = json.load(f)
            if not isinstance(log_data, list): 
                log_data = []
        except (FileNotFoundError, json.JSONDecodeError): 
            log_data = []
            
        log_data.append(interaction_record)
        
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False, default=str)
            
        logger.info(f"Datos guardados exitosamente en {LOG_FILE}")
        return True
    except Exception as e:
        logger.error(f"Error guardando datos: {e}")
        st.error(f"Error al guardar datos: {e}")
        return False

# Inicializar el estado de la sesión
if "state" not in st.session_state:
    st.session_state.state = GraphState(interaction_id=str(uuid.uuid4()))
    st.session_state.messages = [{"role": "assistant", "content": "¡Hola! Soy tu asistente virtual para calcular la huella de carbono de tu empresa. Para comenzar, por favor, dime el nombre de la empresa."}]
    st.session_state.current_task = "esperando_nombre_empresa"
    st.session_state.conversation_finished = False

# Asegurarnos que la API key está configurada
api_key = os.environ.get("GOOGLE_API_KEY", None)
if not api_key:
    api_key = st.text_input("Introduce tu clave API de Google (Gemini)", type="password", key="api_key_input")
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key
        try:
            configure_gemini_client()
            st.success("API de Google configurada correctamente")
        except Exception as e:
            st.error(f"Error al configurar la API: {e}")

# Mostrar el historial de mensajes
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Procesar la entrada del usuario y actualizar el estado
if not st.session_state.conversation_finished:
    # Campo de entrada para el mensaje del usuario
    user_input = st.chat_input("Tu respuesta aquí...")
    
    if user_input:
        # Mostrar el mensaje del usuario
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Añadir el mensaje del usuario al historial
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Actualizar el estado con la entrada del usuario
        st.session_state.state.user_input = user_input
        
        # Procesar la entrada según la tarea actual
        update_dict = {}
        current_task = st.session_state.current_task
        
        if current_task == "esperando_nombre_empresa":
            update_dict = process_company_name_node(st.session_state.state)
        elif current_task == "esperando_nombre_responsable":
            update_dict = process_responsible_name_node(st.session_state.state)
        elif current_task == "esperando_cantidad_empleados":
            update_dict = process_employee_count_node(st.session_state.state)
        elif current_task == "esperando_consumo_luz":
            update_dict = process_electricity_consumption_node(st.session_state.state)
        elif current_task == "esperando_tipo_combustible":
            update_dict = process_fuel_type_node(st.session_state.state)
        elif current_task == "esperando_consumo_combustible":
            update_dict = process_fuel_consumption_node(st.session_state.state)
        elif current_task == "esperando_consumo_gas":
            update_dict = process_gas_consumption_node(st.session_state.state)
        elif current_task == "esperando_distancia_empleados":
            update_dict = process_commute_distance_node(st.session_state.state)
        elif current_task == "esperando_distribucion_transporte":
            # Verificamos qué parte de la distribución estamos procesando
            if not st.session_state.state.transport_pct_car:
                update_dict = process_car_percentage_node(st.session_state.state)
            elif not st.session_state.state.transport_pct_public:
                update_dict = process_public_transport_percentage_node(st.session_state.state)
            else:
                update_dict = process_green_transport_percentage_node(st.session_state.state)
        elif current_task == "esperando_cantidad_residuos":
            update_dict = process_waste_amount_node(st.session_state.state)
        elif current_task == "esperando_porcentaje_reciclaje":
            update_dict = process_recycle_percentage_node(st.session_state.state)
        elif current_task == "esperando_consumo_agua":
            update_dict = process_water_consumption_node(st.session_state.state)
        elif current_task == "esperando_consumo_papel":
            update_dict = process_paper_consumption_node(st.session_state.state)
        elif current_task == "esperando_metros_oficina":
            update_dict = process_office_area_node(st.session_state.state)
        elif current_task == "esperando_tipo_climatizacion":
            update_dict = process_climate_control_node(st.session_state.state)
        elif current_task == "esperando_km_avion":
            update_dict = process_air_travel_node(st.session_state.state)
        elif current_task == "esperando_km_terrestres":
            update_dict = process_ground_travel_node(st.session_state.state)
        elif current_task == "calculando_huella":
            update_dict = calculate_carbon_footprint_node(st.session_state.state)
        
        # Actualizar el estado con el resultado del procesamiento
        for key, value in update_dict.items():
            setattr(st.session_state.state, key, value)
        
        # Obtener los nuevos mensajes (solo el último)
        if 'messages' in update_dict and update_dict['messages']:
            new_message = update_dict['messages'][-1]
            st.session_state.messages.append({"role": "assistant", "content": new_message})
            
            # Mostrar la respuesta del asistente
            with st.chat_message("assistant"):
                st.markdown(new_message)
        
        # Actualizar la tarea actual
        if 'current_task' in update_dict:
            st.session_state.current_task = update_dict['current_task']
        
        # Verificar si la conversación ha terminado
        if 'conversation_finished' in update_dict and update_dict['conversation_finished']:
            st.session_state.conversation_finished = True
            
            # Guardar los datos recopilados
            if save_interaction_data(st.session_state.state):
                st.success("Datos guardados exitosamente. ¡Gracias por completar la información!")
            
            # Añadir botón para reiniciar
            if st.button("Iniciar Nueva Conversación"):
                st.session_state.state = GraphState(interaction_id=str(uuid.uuid4()))
                st.session_state.messages = [{"role": "assistant", "content": "¡Hola! Soy tu asistente virtual para calcular la huella de carbono de tu empresa. Para comenzar, por favor, dime el nombre de la empresa."}]
                st.session_state.current_task = "esperando_nombre_empresa"
                st.session_state.conversation_finished = False
                st.experimental_rerun()
else:
    # Mostrar un resumen de los datos recopilados
    st.subheader("Resumen de Datos Recopilados:")
    
    # Crear un diccionario con los datos más relevantes
    summary_data = {
        "empresa": st.session_state.state.company_name,
        "responsable": st.session_state.state.responsible_name,
        "empleados": st.session_state.state.employee_count,
        "huella_carbono": st.session_state.state.carbon_footprint,
        "huella_por_empleado": st.session_state.state.carbon_per_employee,
        "puntaje_sostenibilidad": st.session_state.state.sustainability_score
    }
    
    st.json(summary_data)
    
    # Añadir botón para reiniciar
    if st.button("Iniciar Nueva Conversación"):
        st.session_state.state = GraphState(interaction_id=str(uuid.uuid4()))
        st.session_state.messages = [{"role": "assistant", "content": "¡Hola! Soy tu asistente virtual para calcular la huella de carbono de tu empresa. Para comenzar, por favor, dime el nombre de la empresa."}]
        st.session_state.current_task = "esperando_nombre_empresa"
        st.session_state.conversation_finished = False
        st.experimental_rerun()

# Información adicional
with st.sidebar:
    st.title("Información")
    st.write("""
    Este chatbot calcula la huella de carbono de tu empresa recopilando información sobre:
    - Consumo energético
    - Transporte de empleados
    - Residuos
    - Agua y papel
    - Infraestructura
    - Viajes
    
    Todos los datos se almacenan localmente en `interactions_log.json`.
    """)
    
    # Mostrar historial de interacciones si existen
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            log_data = json.load(f)
            if log_data:
                st.subheader(f"Interacciones Anteriores: {len(log_data)}")
                for i, entry in enumerate(log_data[-5:]):  # Mostrar las últimas 5
                    st.write(f"**{i+1}.** {entry.get('company_name', 'Desconocido')} - {entry.get('timestamp', '')[:10]}")
    except (FileNotFoundError, json.JSONDecodeError):
        st.write("No hay interacciones anteriores.")
