from typing import Dict, Optional, Any, List
# Importar tipos y estado actualizado
from ..state import GraphState,TaskStateType, IntentType
from ..llm_integration import call_gemini # Quité classify_intent si no se usa
# from ..rules import load_mandaflow_rules # Comentado/Eliminado
# from ..loan_calculator import calculate_loan_options # Comentado/Eliminado
import re
import logging
import math 
import numpy as np
import numpy_financial as npf
import json # Importar json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Mensajes Definidos (Actualizados para Huella de Carbono) ---
WELCOME_MESSAGE = """¡Hola! Soy tu asistente virtual para calcular la huella de carbono de tu empresa.
Para comenzar, por favor, dime el nombre de la empresa."""

COMPANY_NAME_ERROR_MESSAGE = """Disculpa, no pude identificar el nombre de la empresa. ¿Podrías escribirlo de nuevo, por favor?"""
CONFIRM_COMPANY_NAME_MESSAGE = """¡Perfecto! Nombre de la empresa registrado: {company_name}.
Ahora, ¿podrías indicarme tu nombre o el nombre del responsable que está completando esta información?"""

RESPONSIBLE_NAME_ERROR_MESSAGE = """No pude entender el nombre del responsable. ¿Podrías indicármelo de nuevo?"""
CONFIRM_RESPONSIBLE_NAME_MESSAGE = """¡Gracias, {responsible_name}! 
A continuación, necesito saber la cantidad aproximada de empleados que tiene {company_name}."""

EMPLOYEE_COUNT_ERROR_MESSAGE = """No pude entender la cantidad de empleados. Por favor, ingresa un número (ej: 50)."""
CONFIRM_EMPLOYEE_COUNT_MESSAGE = """¡Entendido! {employee_count} empleados registrados.

Ahora comenzaremos con preguntas sobre consumo energético. 
¿Cuál es el consumo mensual aproximado de electricidad en kWh? (Lo encontrarás en tu factura de luz, por ejemplo: 1500 kWh)"""

ELECTRICITY_KWH_ERROR_MESSAGE = """No pude entender el consumo eléctrico. Por favor, ingresa un valor numérico en kWh (ej: 1500)."""
CONFIRM_ELECTRICITY_KWH_MESSAGE = """He registrado un consumo eléctrico de {electricity_kwh} kWh mensuales.

¿Cuál es el principal tipo de combustible que utiliza la empresa? Elige una opción:
1. Gasolina (para vehículos)
2. Diésel (para vehículos o generadores)
3. Gas Natural (para calefacción o procesos)
4. Electricidad (si no usan combustibles fósiles)
5. Ninguno (no utilizan combustibles)"""

FUEL_TYPE_ERROR_MESSAGE = """No pude entender el tipo de combustible. Por favor, indica el número de la opción (1-5) o el nombre del combustible."""
CONFIRM_FUEL_TYPE_MESSAGE = """Registrado: {fuel_type_name} como combustible principal.

¿Cuál es el consumo mensual aproximado de este combustible? Indica la cantidad en {fuel_unit} (ej: 200)."""

FUEL_CONSUMPTION_ERROR_MESSAGE = """No pude entender la cantidad. Por favor, ingresa solo el valor numérico."""
CONFIRM_FUEL_CONSUMPTION_MESSAGE = """He registrado un consumo de {fuel_consumption} {fuel_unit} mensuales de {fuel_type_name}.

¿Cuál es el consumo mensual de gas natural en m³? (Si no utilizan gas natural, ingresa 0)"""

GAS_CONSUMPTION_ERROR_MESSAGE = """No pude entender el consumo de gas. Por favor, ingresa un valor numérico en m³ o 0 si no aplica."""
CONFIRM_GAS_CONSUMPTION_MESSAGE = """Consumo de gas registrado: {gas_consumption} m³ mensuales.

Ahora, hablemos del transporte de los empleados.
¿Cuál es la distancia promedio (en km) que recorre cada empleado diariamente para ir al trabajo? (ida)"""

COMMUTE_DISTANCE_ERROR_MESSAGE = """No pude entender la distancia. Por favor, ingresa un valor numérico en kilómetros."""
CONFIRM_COMMUTE_DISTANCE_MESSAGE = """Distancia promedio registrada: {commute_distance} km (ida).

Aproximadamente, ¿qué porcentaje de tus empleados...
- Utilizan auto particular para ir al trabajo? (ej: 60%)"""

CAR_PCT_ERROR_MESSAGE = """No pude entender el porcentaje. Por favor, ingresa un número entre 0 y 100."""
CONFIRM_CAR_PCT_MESSAGE = """Registrado: {car_pct}% de empleados utilizan auto particular.

¿Qué porcentaje utilizan transporte público (bus, tren, metro, etc.)?"""

PUBLIC_PCT_ERROR_MESSAGE = """No pude entender el porcentaje. Por favor, ingresa un número entre 0 y 100."""
CONFIRM_PUBLIC_PCT_MESSAGE = """Registrado: {public_pct}% de empleados utilizan transporte público.

¿Y qué porcentaje se transportan de forma sostenible (bicicleta, caminando, etc.)?"""

GREEN_PCT_ERROR_MESSAGE = """No pude entender el porcentaje. Por favor, ingresa un número entre 0 y 100."""
CONFIRM_GREEN_PCT_MESSAGE = """Registrado: {green_pct}% de empleados utilizan transporte sostenible.

Ahora hablemos sobre residuos.
¿Cuántos kilogramos aproximados de residuos genera la empresa mensualmente? (ej: 200 kg)"""

WASTE_KG_ERROR_MESSAGE = """No pude entender la cantidad. Por favor, ingresa un valor numérico en kilogramos."""
CONFIRM_WASTE_KG_MESSAGE = """Registrado: {waste_kg} kg de residuos mensuales.

Del total de residuos, ¿qué porcentaje aproximado se recicla? (ej: 30%)"""

RECYCLE_PCT_ERROR_MESSAGE = """No pude entender el porcentaje. Por favor, ingresa un número entre 0 y 100."""
CONFIRM_RECYCLE_PCT_MESSAGE = """Registrado: {recycle_pct}% de residuos reciclados.

Sobre el consumo de agua, ¿cuántos metros cúbicos (m³) de agua consume la empresa mensualmente? (ej: 30 m³)"""

WATER_CONSUMPTION_ERROR_MESSAGE = """No pude entender la cantidad. Por favor, ingresa un valor numérico en m³."""
CONFIRM_WATER_CONSUMPTION_MESSAGE = """Registrado: {water_consumption} m³ de agua mensuales.

¿Cuántos kilogramos de papel consume la empresa mensualmente? (ej: 20 kg)"""

PAPER_CONSUMPTION_ERROR_MESSAGE = """No pude entender la cantidad. Por favor, ingresa un valor numérico en kg."""
CONFIRM_PAPER_CONSUMPTION_MESSAGE = """Registrado: {paper_consumption} kg de papel mensuales.

Sobre la infraestructura, ¿cuántos metros cuadrados (m²) tiene la oficina o instalación principal?"""

OFFICE_SQM_ERROR_MESSAGE = """No pude entender la cantidad. Por favor, ingresa un valor numérico en m²."""
CONFIRM_OFFICE_SQM_MESSAGE = """Registrado: {office_sqm} m² de oficina.

¿Qué sistema de climatización utiliza principalmente? Elige una opción:
1. Aire acondicionado
2. Calefacción a gas
3. Calefacción eléctrica
4. Bomba de calor (más eficiente)
5. Natural (sin sistemas activos)"""

CLIMATE_CONTROL_ERROR_MESSAGE = """No pude entender la opción. Por favor, indica el número (1-5) o el tipo de sistema."""
CONFIRM_CLIMATE_CONTROL_MESSAGE = """Registrado: {climate_control_name} como sistema principal de climatización.

Por último, hablemos de viajes corporativos.
¿Cuántos kilómetros mensuales recorren en total los empleados en viajes de avión? (Si no hacen viajes, ingresa 0)"""

AIR_TRAVEL_ERROR_MESSAGE = """No pude entender la cantidad. Por favor, ingresa un valor numérico en km o 0 si no aplica."""
CONFIRM_AIR_TRAVEL_MESSAGE = """Registrado: {air_travel} km mensuales en avión.

¿Y cuántos kilómetros mensuales recorren en total en viajes terrestres de larga distancia (tren, bus)? (0 si no aplica)"""

GROUND_TRAVEL_ERROR_MESSAGE = """No pude entender la cantidad. Por favor, ingresa un valor numérico en km o 0 si no aplica."""
CONFIRM_GROUND_TRAVEL_MESSAGE = """Registrado: {ground_travel} km mensuales en viajes terrestres.

¡Perfecto! He recopilado toda la información necesaria. Ahora calcularé la huella de carbono de {company_name}..."""

CALCULATING_MESSAGE = """Procesando datos y calculando la huella de carbono..."""

RESULT_MESSAGE = """
¡Análisis completado! Resultados para {company_name}:

📊 HUELLA DE CARBONO TOTAL: {total_footprint:.2f} toneladas CO₂e mensuales
👤 HUELLA POR EMPLEADO: {per_employee:.2f} toneladas CO₂e mensuales

🏆 PUNTAJE DE SOSTENIBILIDAD: {score}/100 - {category}

📋 DESGLOSE POR CATEGORÍA:
{breakdown}

💡 RECOMENDACIONES:
{recommendations}

Gracias por utilizar nuestra calculadora de huella de carbono. Con estos datos puedes comenzar a implementar estrategias para reducir el impacto ambiental de tu empresa.
"""

# --- Función de Extracción (Podríamos necesitar nuevas o adaptar) ---
# def extract_amount(text: str) -> Optional[float]: ... (Ya no se necesita directamente)
# Podríamos tener extract_number, extract_name, etc. o usar el LLM.

# --- Helper para extraer número (Versión mejorada) ---
def extract_numeric_value(text: str, context: str) -> Optional[float]:
    """Intenta extraer un valor numérico usando validación directa primero y luego LLM si es necesario."""
    if not text or not text.strip():
        logger.warning(f"Input vacío para contexto: {context}")
        return None
    
    # PRIMERO: Intentar conversión directa para casos simples como "5", "10.5", etc.
    try:
        # Si el input es directamente un número, convertirlo y devolver
        cleaned_text = text.strip()
        return float(cleaned_text)
    except ValueError:
        # Si no es un número directo, intentar con regex para casos como "5 empleados"
        import re
        numeric_match = re.search(r'(\d+(?:\.\d+)?)', cleaned_text)
        if numeric_match:
            try:
                number = float(numeric_match.group(1))
                logger.info(f"Extracción directa: Número {number} encontrado en '{text}' para {context}")
                return number
            except ValueError:
                # Continuar con LLM si la extracción regex falla
                pass
    
    # SEGUNDO: Si la validación directa falla, usar LLM para casos más complejos
    # como "cinco", "5k", "cinco mil", etc.
    prompt = f"""El usuario ha respondido '{text}' a la pregunta sobre '{context}'.
Extrae SOLO el valor numérico, ignorando texto y símbolos de moneda.
Si dice 'mil' o 'k', interpreta como multiplicación por 1000.
Si hay un número claro, devuelve solo ese número como flotante (ej: 15000.0).
Si no hay ningún número claro o identificable, responde solo 'None'.

Recuerda, tu única respuesta debe ser un número o 'None'. Nada más."""
    
    try:
        response = call_gemini(prompt, temperature=0.1, max_output_tokens=50)
        if response and response.strip().lower() != 'none':
            try:
                # Limpieza básica - eliminar todo menos dígitos, punto y coma
                cleaned_response = re.sub(r'[^\d.,]', '', response)
                # Convertir coma a punto si hay
                cleaned_response = cleaned_response.replace(',', '.')
                number = float(cleaned_response)
                logger.info(f"Extracción LLM: Número {number} extraído de '{text}' para {context}")
                return number
            except ValueError:
                logger.warning(f"No se pudo convertir la respuesta del LLM '{response}' a número.")
                return None
        logger.info(f"LLM no extrajo número para '{context}'. Respuesta: {response}")
        return None
    except Exception as e:
        logger.error(f"Error durante la extracción numérica: {e}", exc_info=True)
        return None

# --- Nodos ---

def start_node(state: GraphState) -> Dict[str, Any]:
    """Nodo inicial. Da la bienvenida y pide el nombre de la empresa."""
    logger.info("--- Iniciando conversación: Recolección de Datos Empresa ---")
    # La tarea inicial después de saludar es esperar el nombre de la empresa
    return {"messages": [WELCOME_MESSAGE], "current_task": "esperando_nombre_empresa"}

# NUEVO NODO: Procesar el nombre de la empresa
def process_company_name_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta del usuario para obtener el nombre de la empresa."""
    logger.info("--- Procesando Nombre Empresa ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    company_name: Optional[str] = None
    next_task: TaskStateType = "esperando_nombre_empresa" # Por defecto, re-pregunta
    response_message = COMPANY_NAME_ERROR_MESSAGE

    if user_input and user_input.strip():
        # Podríamos usar el LLM aquí para una extracción más robusta,
        # pero para un nombre de empresa, a menudo basta con tomar el input directo.
        # O podríamos usar el LLM para validar/limpiar.
        # Ejemplo simple:
        company_name = user_input.strip()
        logger.info(f"Nombre Empresa extraído: {company_name}")
        # Prepara el mensaje de confirmación y la siguiente pregunta
        response_message = CONFIRM_COMPANY_NAME_MESSAGE.format(company_name=company_name)
        # Avanza a la siguiente tarea
        next_task = "esperando_nombre_responsable"
    else:
        logger.warning("Input nombre empresa vacío.")
        # Mantiene la tarea y mensaje de error

    return {
        "company_name": company_name, # Actualiza el estado
        "messages": current_messages + [response_message], # Añade el mensaje de respuesta/error
        "current_task": next_task, # Define la siguiente tarea
        "last_user_intent": None, # Resetea la intención (o podría clasificarse)
        "user_input": None # Limpia el input procesado
    }

# NUEVO NODO: Procesar el nombre del responsable
def process_responsible_name_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta del usuario para obtener el nombre del responsable."""
    logger.info("--- Procesando Nombre Responsable ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    responsible_name: Optional[str] = None
    next_task: TaskStateType = "esperando_nombre_responsable"
    response_message = RESPONSIBLE_NAME_ERROR_MESSAGE

    if user_input and user_input.strip():
        responsible_name = user_input.strip()
        logger.info(f"Nombre Responsable extraído: {responsible_name}")
        # Incluir el nombre de la empresa en el mensaje
        response_message = CONFIRM_RESPONSIBLE_NAME_MESSAGE.format(
            responsible_name=responsible_name,
            company_name=state.company_name or "tu empresa"
        )
        next_task = "esperando_cantidad_empleados"
    else:
        logger.warning("Input nombre responsable vacío.")

    return {
        "responsible_name": responsible_name,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Preguntar cantidad de empleados (ya la pregunta está en el mensaje anterior)
# No necesitamos un nodo 'ask_responsible_name' separado porque la pregunta
# se hace directamente en el mensaje de confirmación del nodo anterior (CONFIRM_COMPANY_NAME_MESSAGE).
# Lo mismo aplica para la pregunta de cantidad de empleados.
# Solo necesitamos los nodos 'process_...' para manejar la respuesta.

# >> NUEVO NODO <<
def process_employee_count_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener la cantidad de empleados."""
    logger.info("--- Procesando Cantidad Empleados ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    employee_count: Optional[int] = None
    next_task: TaskStateType = "esperando_cantidad_empleados"
    response_message = EMPLOYEE_COUNT_ERROR_MESSAGE

    numeric_value = extract_numeric_value(user_input, "cantidad de empleados")

    if numeric_value is not None and numeric_value >= 0:
        employee_count = int(numeric_value)  # Convertir a entero ya que son personas
        logger.info(f"Cantidad Empleados extraída: {employee_count}")
        response_message = CONFIRM_EMPLOYEE_COUNT_MESSAGE.format(employee_count=employee_count)
        next_task = "esperando_consumo_luz"  # Cambiado: ahora preguntamos por kWh, no por gasto
    else:
        logger.warning(f"No se pudo extraer número válido de empleados de: {user_input}")

    return {
        "employee_count": employee_count,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Procesar consumo de electricidad en kWh
def process_electricity_consumption_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener el consumo eléctrico en kWh."""
    logger.info("--- Procesando Consumo Eléctrico ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    electricity_kwh: Optional[float] = None
    next_task: TaskStateType = "esperando_consumo_luz"
    response_message = ELECTRICITY_KWH_ERROR_MESSAGE

    numeric_value = extract_numeric_value(user_input, "consumo eléctrico en kWh")

    if numeric_value is not None and numeric_value >= 0:
        electricity_kwh = numeric_value
        logger.info(f"Consumo eléctrico extraído: {electricity_kwh} kWh")
        response_message = CONFIRM_ELECTRICITY_KWH_MESSAGE.format(electricity_kwh=electricity_kwh)
        next_task = "esperando_tipo_combustible"
    else:
        logger.warning(f"No se pudo extraer consumo eléctrico válido de: {user_input}")

    return {
        "electricity_kwh": electricity_kwh,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Procesar tipo de combustible
def process_fuel_type_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener el tipo de combustible principal."""
    logger.info("--- Procesando Tipo de Combustible ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    fuel_type = None
    fuel_type_name = ""
    fuel_unit = ""
    next_task: TaskStateType = "esperando_tipo_combustible"
    response_message = FUEL_TYPE_ERROR_MESSAGE

    if user_input and user_input.strip():
        # Mapeo de respuestas posibles a tipos de combustible
        fuel_types_map = {
            "1": "gasolina", "gasolina": "gasolina", "nafta": "gasolina",
            "2": "diesel", "diesel": "diesel", "diésel": "diesel", "gasoil": "diesel",
            "3": "gas_natural", "gas natural": "gas_natural", "gas": "gas_natural",
            "4": "electricidad", "eléctrico": "electricidad", "electrico": "electricidad",
            "5": "ninguno", "no": "ninguno", "nada": "ninguno", "no aplica": "ninguno"
        }
        
        # Buscar en el mapa
        cleaned_input = user_input.strip().lower()
        fuel_type = fuel_types_map.get(cleaned_input)
        
        if fuel_type:
            # Nombres descriptivos y unidades para mostrar al usuario
            fuel_names = {
                "gasolina": "Gasolina", 
                "diesel": "Diésel",
                "gas_natural": "Gas Natural",
                "electricidad": "Electricidad",
                "ninguno": "Ningún combustible"
            }
            
            fuel_units = {
                "gasolina": "litros",
                "diesel": "litros",
                "gas_natural": "m³",
                "electricidad": "kWh",
                "ninguno": "unidades"
            }
            
            fuel_type_name = fuel_names.get(fuel_type, fuel_type)
            fuel_unit = fuel_units.get(fuel_type, "unidades")
            
            logger.info(f"Tipo de combustible extraído: {fuel_type} (Nombre: {fuel_type_name}, Unidad: {fuel_unit})")
            
            # Para combustibles que no requieren cantidad, saltar a la siguiente pregunta
            if fuel_type in ["electricidad", "ninguno"]:
                response_message = f"Registrado: {fuel_type_name} como fuente principal. No es necesario especificar consumo adicional.\n\n¿Cuál es el consumo mensual de gas natural en m³? (Si no utilizan gas natural, ingresa 0)"
                next_task = "esperando_consumo_gas"
            else:
                response_message = CONFIRM_FUEL_TYPE_MESSAGE.format(
                    fuel_type_name=fuel_type_name,
                    fuel_unit=fuel_unit
                )
                next_task = "esperando_consumo_combustible"
        else:
            logger.warning(f"No se pudo reconocer el tipo de combustible: {user_input}")
    else:
        logger.warning("Input tipo combustible vacío.")

    return {
        "fuel_type": fuel_type,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Procesar consumo de combustible
def process_fuel_consumption_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener el consumo de combustible."""
    logger.info("--- Procesando Consumo de Combustible ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    fuel_consumption: Optional[float] = None
    next_task: TaskStateType = "esperando_consumo_combustible"
    response_message = FUEL_CONSUMPTION_ERROR_MESSAGE

    # Obtener el tipo de combustible y la unidad para el mensaje
    fuel_type = state.fuel_type or "gasolina"  # Default por si acaso
    fuel_units = {
        "gasolina": "litros",
        "diesel": "litros",
        "gas_natural": "m³",
        "electricidad": "kWh",
        "ninguno": "unidades"
    }
    fuel_unit = fuel_units.get(fuel_type, "unidades")
    
    fuel_names = {
        "gasolina": "Gasolina", 
        "diesel": "Diésel",
        "gas_natural": "Gas Natural",
        "electricidad": "Electricidad",
        "ninguno": "Ningún combustible"
    }
    fuel_type_name = fuel_names.get(fuel_type, fuel_type)

    numeric_value = extract_numeric_value(user_input, f"consumo de {fuel_type}")

    if numeric_value is not None and numeric_value >= 0:
        fuel_consumption = numeric_value
        logger.info(f"Consumo de {fuel_type} extraído: {fuel_consumption} {fuel_unit}")
        response_message = CONFIRM_FUEL_CONSUMPTION_MESSAGE.format(
            fuel_consumption=fuel_consumption,
            fuel_unit=fuel_unit,
            fuel_type_name=fuel_type_name
        )
        next_task = "esperando_consumo_gas"
    else:
        logger.warning(f"No se pudo extraer consumo de combustible válido de: {user_input}")

    return {
        "fuel_consumption": fuel_consumption,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Procesar consumo de gas
def process_gas_consumption_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener el consumo de gas natural."""
    logger.info("--- Procesando Consumo de Gas ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    gas_consumption: Optional[float] = None
    next_task: TaskStateType = "esperando_consumo_gas"
    response_message = GAS_CONSUMPTION_ERROR_MESSAGE

    # Verificar si la respuesta indica "no consumo" de forma textual
    no_consumption_keywords = ["no", "cero", "0", "nada", "no usamos", "no tenemos", "no aplica"]
    if user_input and any(keyword in user_input.lower() for keyword in no_consumption_keywords):
        gas_consumption = 0
        logger.info("Consumo de gas: 0 (indicación textual de no consumo)")
        response_message = CONFIRM_GAS_CONSUMPTION_MESSAGE.format(gas_consumption=0)
        next_task = "esperando_distancia_empleados"
    else:
        numeric_value = extract_numeric_value(user_input, "consumo de gas natural")
        
        if numeric_value is not None and numeric_value >= 0:
            gas_consumption = numeric_value
            logger.info(f"Consumo de gas extraído: {gas_consumption} m³")
            response_message = CONFIRM_GAS_CONSUMPTION_MESSAGE.format(gas_consumption=gas_consumption)
            next_task = "esperando_distancia_empleados"
        else:
            logger.warning(f"No se pudo extraer consumo de gas válido de: {user_input}")

    return {
        "gas_consumption": gas_consumption,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Procesar distancia de transporte de empleados
def process_commute_distance_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener la distancia promedio de transporte."""
    logger.info("--- Procesando Distancia de Transporte ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    commute_distance: Optional[float] = None
    next_task: TaskStateType = "esperando_distancia_empleados"
    response_message = COMMUTE_DISTANCE_ERROR_MESSAGE

    numeric_value = extract_numeric_value(user_input, "distancia de transporte")

    if numeric_value is not None and numeric_value >= 0:
        commute_distance = numeric_value
        logger.info(f"Distancia de transporte extraída: {commute_distance} km")
        response_message = CONFIRM_COMMUTE_DISTANCE_MESSAGE.format(commute_distance=commute_distance)
        next_task = "esperando_distribucion_transporte"
    else:
        logger.warning(f"No se pudo extraer distancia de transporte válida de: {user_input}")

    return {
        "employee_commute_distance": commute_distance,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Procesar porcentaje de empleados que usan auto
def process_car_percentage_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener el porcentaje de empleados que usan auto."""
    logger.info("--- Procesando Porcentaje Auto ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    car_pct: Optional[int] = None
    next_task: TaskStateType = "esperando_distribucion_transporte"
    response_message = CAR_PCT_ERROR_MESSAGE

    # Extraer número o porcentaje
    numeric_value = extract_numeric_value(user_input, "porcentaje en auto")

    if numeric_value is not None:
        # Limitar al rango 0-100
        car_pct = min(100, max(0, int(numeric_value)))
        logger.info(f"Porcentaje auto extraído: {car_pct}%")
        response_message = CONFIRM_CAR_PCT_MESSAGE.format(car_pct=car_pct)
        next_task = "esperando_distribucion_transporte"  # La siguiente pregunta es sobre transporte público
        return {
            "transport_pct_car": car_pct,
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }
    else:
        logger.warning(f"No se pudo extraer porcentaje de auto válido de: {user_input}")
        return {
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }

# NUEVO NODO: Procesar porcentaje de empleados que usan transporte público
def process_public_transport_percentage_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener el porcentaje de empleados que usan transporte público."""
    logger.info("--- Procesando Porcentaje Transporte Público ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    public_pct: Optional[int] = None
    next_task: TaskStateType = "esperando_distribucion_transporte"  # Mismo task, pero ahora se pregunta por verde
    response_message = PUBLIC_PCT_ERROR_MESSAGE

    # Extraer número o porcentaje
    numeric_value = extract_numeric_value(user_input, "porcentaje en transporte público")

    if numeric_value is not None:
        # Limitar al rango 0-100
        public_pct = min(100, max(0, int(numeric_value)))
        logger.info(f"Porcentaje transporte público extraído: {public_pct}%")
        
        # Verificar que los porcentajes no superan 100% (con auto)
        car_pct = state.transport_pct_car or 0
        if car_pct + public_pct > 100:
            logger.warning(f"Los porcentajes de auto ({car_pct}%) y transporte público ({public_pct}%) superan 100%. Ajustando...")
            public_pct = 100 - car_pct
        
        response_message = CONFIRM_PUBLIC_PCT_MESSAGE.format(public_pct=public_pct)
        next_task = "esperando_distribucion_transporte"  # La siguiente pregunta es sobre transporte verde
        return {
            "transport_pct_public": public_pct,
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }
    else:
        logger.warning(f"No se pudo extraer porcentaje de transporte público válido de: {user_input}")
        return {
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }

# NUEVO NODO: Procesar porcentaje de empleados que usan transporte sostenible
def process_green_transport_percentage_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener el porcentaje de empleados que usan transporte sostenible."""
    logger.info("--- Procesando Porcentaje Transporte Sostenible ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    green_pct: Optional[int] = None
    next_task: TaskStateType = "esperando_distribucion_transporte"
    response_message = GREEN_PCT_ERROR_MESSAGE

    # Extraer número o porcentaje
    numeric_value = extract_numeric_value(user_input, "porcentaje en transporte sostenible")

    if numeric_value is not None:
        # Limitar al rango 0-100
        green_pct = min(100, max(0, int(numeric_value)))
        logger.info(f"Porcentaje transporte sostenible extraído: {green_pct}%")
        
        # Verificar que los porcentajes no superan 100% (con auto y público)
        car_pct = state.transport_pct_car or 0
        public_pct = state.transport_pct_public or 0
        if car_pct + public_pct + green_pct > 100:
            logger.warning(f"Los porcentajes de auto ({car_pct}%), público ({public_pct}%) y sostenible ({green_pct}%) superan 100%. Ajustando...")
            green_pct = 100 - (car_pct + public_pct)
            if green_pct < 0:
                green_pct = 0
        
        response_message = CONFIRM_GREEN_PCT_MESSAGE.format(green_pct=green_pct)
        next_task = "esperando_cantidad_residuos"  # Pasamos a la siguiente categoría: residuos
        return {
            "transport_pct_green": green_pct,
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }
    else:
        logger.warning(f"No se pudo extraer porcentaje de transporte sostenible válido de: {user_input}")
        return {
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }

# NUEVO NODO: Procesar cantidad de residuos
def process_waste_amount_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener la cantidad de residuos generados."""
    logger.info("--- Procesando Cantidad Residuos ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    waste_kg: Optional[float] = None
    next_task: TaskStateType = "esperando_cantidad_residuos"
    response_message = WASTE_KG_ERROR_MESSAGE

    numeric_value = extract_numeric_value(user_input, "cantidad de residuos")

    if numeric_value is not None and numeric_value >= 0:
        waste_kg = numeric_value
        logger.info(f"Cantidad de residuos extraída: {waste_kg} kg")
        response_message = CONFIRM_WASTE_KG_MESSAGE.format(waste_kg=waste_kg)
        next_task = "esperando_porcentaje_reciclaje"
    else:
        logger.warning(f"No se pudo extraer cantidad de residuos válida de: {user_input}")

    return {
        "waste_kg": waste_kg,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Procesar porcentaje de reciclaje
def process_recycle_percentage_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener el porcentaje de residuos reciclados."""
    logger.info("--- Procesando Porcentaje Reciclaje ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    recycle_pct: Optional[int] = None
    next_task: TaskStateType = "esperando_porcentaje_reciclaje"
    response_message = RECYCLE_PCT_ERROR_MESSAGE

    # Manejar respuestas del tipo "nada" o "no reciclamos"
    no_recycle_keywords = ["no", "nada", "cero", "0", "ninguno", "no reciclamos"]
    if user_input and any(keyword in user_input.lower() for keyword in no_recycle_keywords):
        recycle_pct = 0
        logger.info("Porcentaje reciclaje: 0% (indicación textual de no reciclaje)")
        response_message = CONFIRM_RECYCLE_PCT_MESSAGE.format(recycle_pct=0)
        next_task = "esperando_consumo_agua"
        return {
            "recycle_pct": recycle_pct,
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }

    # Extraer número o porcentaje
    numeric_value = extract_numeric_value(user_input, "porcentaje de reciclaje")

    if numeric_value is not None:
        # Limitar al rango 0-100
        recycle_pct = min(100, max(0, int(numeric_value)))
        logger.info(f"Porcentaje reciclaje extraído: {recycle_pct}%")
        response_message = CONFIRM_RECYCLE_PCT_MESSAGE.format(recycle_pct=recycle_pct)
        next_task = "esperando_consumo_agua"
        return {
            "recycle_pct": recycle_pct,
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }
    else:
        logger.warning(f"No se pudo extraer porcentaje de reciclaje válido de: {user_input}")
        return {
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }

# NUEVO NODO: Procesar consumo de agua
def process_water_consumption_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener el consumo de agua."""
    logger.info("--- Procesando Consumo Agua ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    water_consumption: Optional[float] = None
    next_task: TaskStateType = "esperando_consumo_agua"
    response_message = WATER_CONSUMPTION_ERROR_MESSAGE

    # Manejar respuestas del tipo "no sabemos" o "desconocido"
    unknown_keywords = ["no sé", "no se", "desconocido", "no sabemos", "no tengo idea", "no tenemos el dato"]
    if user_input and any(keyword in user_input.lower() for keyword in unknown_keywords):
        # Usar un valor promedio conservador basado en el número de empleados (aprox. 1 m³ por empleado al mes)
        if state.employee_count:
            water_consumption = state.employee_count * 1.0
            logger.info(f"Consumo de agua estimado: {water_consumption} m³ (basado en {state.employee_count} empleados)")
            response_message = f"Entiendo que no tienes el dato exacto. He estimado un consumo aproximado de {water_consumption} m³ basado en el número de empleados.\n\n¿Cuántos kilogramos de papel consume la empresa mensualmente? (ej: 20 kg)"
            next_task = "esperando_consumo_papel"
            return {
                "water_consumption": water_consumption,
                "messages": current_messages + [response_message],
                "current_task": next_task,
                "last_user_intent": None,
                "user_input": None
            }

    numeric_value = extract_numeric_value(user_input, "consumo de agua")

    if numeric_value is not None and numeric_value >= 0:
        water_consumption = numeric_value
        logger.info(f"Consumo de agua extraído: {water_consumption} m³")
        response_message = CONFIRM_WATER_CONSUMPTION_MESSAGE.format(water_consumption=water_consumption)
        next_task = "esperando_consumo_papel"
    else:
        logger.warning(f"No se pudo extraer consumo de agua válido de: {user_input}")

    return {
        "water_consumption": water_consumption,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Procesar consumo de papel
def process_paper_consumption_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener el consumo de papel."""
    logger.info("--- Procesando Consumo Papel ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    paper_consumption: Optional[float] = None
    next_task: TaskStateType = "esperando_consumo_papel"
    response_message = PAPER_CONSUMPTION_ERROR_MESSAGE

    # Manejar respuestas del tipo "no sabemos" o "poco"
    unknown_keywords = ["no sé", "no se", "desconocido", "no sabemos", "no tengo idea", "poco", "muy poco"]
    if user_input and any(keyword in user_input.lower() for keyword in unknown_keywords):
        # Usar un valor promedio conservador (aprox. 1 kg por empleado al mes)
        if state.employee_count:
            paper_consumption = state.employee_count * 1.0
            logger.info(f"Consumo de papel estimado: {paper_consumption} kg (basado en {state.employee_count} empleados)")
            response_message = f"Entiendo que no tienes el dato exacto. He estimado un consumo aproximado de {paper_consumption} kg basado en el número de empleados.\n\n¿Cuántos metros cuadrados (m²) tiene la oficina o instalación principal?"
            next_task = "esperando_metros_oficina"
            return {
                "paper_consumption": paper_consumption,
                "messages": current_messages + [response_message],
                "current_task": next_task,
                "last_user_intent": None,
                "user_input": None
            }

    numeric_value = extract_numeric_value(user_input, "consumo de papel")

    if numeric_value is not None and numeric_value >= 0:
        paper_consumption = numeric_value
        logger.info(f"Consumo de papel extraído: {paper_consumption} kg")
        response_message = CONFIRM_PAPER_CONSUMPTION_MESSAGE.format(paper_consumption=paper_consumption)
        next_task = "esperando_metros_oficina"
    else:
        logger.warning(f"No se pudo extraer consumo de papel válido de: {user_input}")

    return {
        "paper_consumption": paper_consumption,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Procesar metros cuadrados de oficina
def process_office_area_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener los metros cuadrados de la oficina."""
    logger.info("--- Procesando Metros Cuadrados Oficina ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    office_sqm: Optional[float] = None
    next_task: TaskStateType = "esperando_metros_oficina"
    response_message = OFFICE_SQM_ERROR_MESSAGE

    # Manejar estimaciones basadas en número de empleados
    if not user_input or "no sé" in user_input.lower() or "no tengo" in user_input.lower():
        # Estimar basado en empleados (aprox. 10m² por empleado)
        if state.employee_count:
            office_sqm = state.employee_count * 10.0
            logger.info(f"Metros cuadrados estimados: {office_sqm} m² (basado en {state.employee_count} empleados)")
            response_message = f"Entiendo que no tienes el dato exacto. He estimado aproximadamente {office_sqm} m² basado en el número de empleados.\n\n¿Qué sistema de climatización utiliza principalmente? Elige una opción:\n1. Aire acondicionado\n2. Calefacción a gas\n3. Calefacción eléctrica\n4. Bomba de calor (más eficiente)\n5. Natural (sin sistemas activos)"
            next_task = "esperando_tipo_climatizacion"
            return {
                "office_sqm": office_sqm,
                "messages": current_messages + [response_message],
                "current_task": next_task,
                "last_user_intent": None,
                "user_input": None
            }

    numeric_value = extract_numeric_value(user_input, "metros cuadrados")

    if numeric_value is not None and numeric_value > 0:
        office_sqm = numeric_value
        logger.info(f"Metros cuadrados extraídos: {office_sqm} m²")
        response_message = CONFIRM_OFFICE_SQM_MESSAGE.format(office_sqm=office_sqm)
        next_task = "esperando_tipo_climatizacion"
    else:
        logger.warning(f"No se pudo extraer metros cuadrados válidos de: {user_input}")

    return {
        "office_sqm": office_sqm,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Procesar tipo de climatización
def process_climate_control_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener el tipo de climatización."""
    logger.info("--- Procesando Tipo Climatización ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    climate_control = None
    next_task: TaskStateType = "esperando_tipo_climatizacion"
    response_message = CLIMATE_CONTROL_ERROR_MESSAGE

    if user_input and user_input.strip():
        # Mapeo de respuestas posibles a tipos de climatización
        climate_map = {
            "1": "aire_acondicionado", "aire": "aire_acondicionado", "aire acondicionado": "aire_acondicionado", "a/c": "aire_acondicionado",
            "2": "calefaccion_gas", "calefaccion gas": "calefaccion_gas", "gas": "calefaccion_gas", "caldera": "calefaccion_gas",
            "3": "calefaccion_electrica", "electrica": "calefaccion_electrica", "eléctrica": "calefaccion_electrica", "radiadores": "calefaccion_electrica",
            "4": "bomba_calor", "bomba": "bomba_calor", "bomba de calor": "bomba_calor", "aerotermia": "bomba_calor",
            "5": "natural", "no hay": "natural", "ninguno": "natural", "ventilacion natural": "natural", "ventanas": "natural"
        }
        
        # Buscar en el mapa
        cleaned_input = user_input.strip().lower()
        climate_control = climate_map.get(cleaned_input)
        
        if climate_control:
            # Nombres descriptivos para mostrar al usuario
            climate_names = {
                "aire_acondicionado": "Aire acondicionado", 
                "calefaccion_gas": "Calefacción a gas",
                "calefaccion_electrica": "Calefacción eléctrica",
                "bomba_calor": "Bomba de calor",
                "natural": "Ventilación natural"
            }
            
            climate_control_name = climate_names.get(climate_control, climate_control)
            
            logger.info(f"Tipo de climatización extraído: {climate_control} (Nombre: {climate_control_name})")
            response_message = CONFIRM_CLIMATE_CONTROL_MESSAGE.format(climate_control_name=climate_control_name)
            next_task = "esperando_km_avion"
        else:
            logger.warning(f"No se pudo reconocer el tipo de climatización: {user_input}")
    else:
        logger.warning("Input tipo climatización vacío.")

    return {
        "climate_control": climate_control,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Procesar kilómetros en avión
def process_air_travel_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener los kilómetros de viajes en avión."""
    logger.info("--- Procesando Viajes Avión ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    air_travel: Optional[float] = None
    next_task: TaskStateType = "esperando_km_avion"
    response_message = AIR_TRAVEL_ERROR_MESSAGE

    # Manejar respuestas del tipo "no viajamos" o "cero"
    no_travel_keywords = ["no", "cero", "0", "ninguno", "no viajamos", "nada", "no hay", "no aplica"]
    if user_input and any(keyword in user_input.lower() for keyword in no_travel_keywords):
        air_travel = 0
        logger.info("Viajes avión: 0 km (indicación textual de no viajes)")
        response_message = CONFIRM_AIR_TRAVEL_MESSAGE.format(air_travel=0)
        next_task = "esperando_km_terrestres"
        return {
            "air_travel_km": air_travel,
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }

    # Intentar extraer directamente un número si es un valor numérico simple
    if user_input and user_input.strip().replace(" ", "").isdigit():
        air_travel = float(user_input.strip())
        logger.info(f"Kilómetros en avión extraídos directamente: {air_travel} km")
        response_message = CONFIRM_AIR_TRAVEL_MESSAGE.format(air_travel=air_travel)
        next_task = "esperando_km_terrestres"
        return {
            "air_travel_km": air_travel,
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }

    # Si no es un número simple, usar el extractor numérico
    numeric_value = extract_numeric_value(user_input, "kilómetros en avión")

    if numeric_value is not None and numeric_value >= 0:
        air_travel = numeric_value
        logger.info(f"Kilómetros en avión extraídos: {air_travel} km")
        response_message = CONFIRM_AIR_TRAVEL_MESSAGE.format(air_travel=air_travel)
        next_task = "esperando_km_terrestres"
    else:
        logger.warning(f"No se pudo extraer kilómetros en avión válidos de: {user_input}")

    return {
        "air_travel_km": air_travel,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Procesar kilómetros en viajes terrestres
def process_ground_travel_node(state: GraphState) -> Dict[str, Any]:
    """Procesa la respuesta para obtener los kilómetros de viajes terrestres."""
    logger.info("--- Procesando Viajes Terrestres ---")
    user_input = state.user_input
    current_messages = getattr(state, 'messages', [])
    ground_travel: Optional[float] = None
    next_task: TaskStateType = "esperando_km_terrestres"
    response_message = GROUND_TRAVEL_ERROR_MESSAGE

    # Manejar respuestas del tipo "no viajamos" o "cero"
    no_travel_keywords = ["no", "cero", "0", "ninguno", "no viajamos", "nada", "no hay", "no aplica"]
    if user_input and any(keyword in user_input.lower() for keyword in no_travel_keywords):
        ground_travel = 0
        logger.info("Viajes terrestres: 0 km (indicación textual de no viajes)")
        company_name = state.company_name or "tu empresa"
        response_message = CONFIRM_GROUND_TRAVEL_MESSAGE.format(ground_travel=0, company_name=company_name)
        next_task = "calculando_huella"
        return {
            "ground_travel_km": ground_travel,
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }

    # Intentar extraer directamente un número si es un valor numérico simple
    if user_input and user_input.strip().replace(" ", "").isdigit():
        ground_travel = float(user_input.strip())
        logger.info(f"Kilómetros terrestres extraídos directamente: {ground_travel} km")
        
        # Obtener el nombre de la empresa para el mensaje de confirmación
        company_name = state.company_name or "tu empresa"
        
        # Mensaje final que confirma los viajes terrestres y anuncia el cálculo
        response_message = CONFIRM_GROUND_TRAVEL_MESSAGE.format(ground_travel=ground_travel, company_name=company_name)
        
        # Añadir mensaje de que se está calculando
        response_message += "\n\n" + CALCULATING_MESSAGE
        
        next_task = "calculando_huella"
        return {
            "ground_travel_km": ground_travel,
            "messages": current_messages + [response_message],
            "current_task": next_task,
            "last_user_intent": None,
            "user_input": None
        }

    # Si no es un número simple, usar el extractor numérico
    numeric_value = extract_numeric_value(user_input, "kilómetros terrestres")

    if numeric_value is not None and numeric_value >= 0:
        ground_travel = numeric_value
        logger.info(f"Kilómetros terrestres extraídos: {ground_travel} km")
        
        # Obtener el nombre de la empresa para el mensaje de confirmación
        company_name = state.company_name or "tu empresa"
        
        # Mensaje final que confirma los viajes terrestres y anuncia el cálculo
        response_message = CONFIRM_GROUND_TRAVEL_MESSAGE.format(ground_travel=ground_travel, company_name=company_name)
        
        # Añadir mensaje de que se está calculando
        response_message += "\n\n" + CALCULATING_MESSAGE
        
        next_task = "calculando_huella"
    else:
        logger.warning(f"No se pudo extraer kilómetros terrestres válidos de: {user_input}")

    return {
        "ground_travel_km": ground_travel,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "last_user_intent": None,
        "user_input": None
    }

# NUEVO NODO: Calcular huella de carbono
from ..carbon_calculator import calculate_carbon_footprint, get_score_category, get_recommendations

def calculate_carbon_footprint_node(state: GraphState) -> Dict[str, Any]:
    """Calcula la huella de carbono basada en los datos recolectados."""
    logger.info("--- Calculando Huella de Carbono ---")
    current_messages = getattr(state, 'messages', [])
    next_task: TaskStateType = "mostrando_resultados"
    
    # Obtener país (default por ahora)
    country = "default"
    
    try:
        # Calcular huella de carbono
        results = calculate_carbon_footprint(state, country)
        
        # Extraer resultados principales
        total_footprint = results.get("total_footprint", 0)
        per_employee = results.get("per_employee", 0)
        breakdown = results.get("breakdown", {})
        sustainability_score = results.get("sustainability_score", 50)
        
        # Obtener categoría según puntaje
        category = get_score_category(sustainability_score)
        
        # Obtener recomendaciones personalizadas
        recommendations = get_recommendations(state, sustainability_score)
        
        # Formatear desglose para presentación
        breakdown_formatted = ""
        for category, value in breakdown.items():
            # Traducir nombres de categorías
            category_names = {
                "electricidad": "Electricidad",
                "combustible": "Combustible",
                "gas": "Gas Natural",
                "transporte_empleados": "Transporte Empleados",
                "residuos": "Residuos",
                "agua": "Agua",
                "papel": "Papel",
                "infraestructura": "Infraestructura",
                "viajes": "Viajes Corporativos"
            }
            category_name = category_names.get(category, category)
            
            # Incluir solo categorías con valor > 0
            if value > 0.001:
                breakdown_formatted += f"• {category_name}: {value:.2f} toneladas CO₂e\n"
        
        # Formatear recomendaciones
        recommendations_formatted = "\n".join([f"• {rec}" for rec in recommendations])
        
        # Mensaje de resultados
        response_message = RESULT_MESSAGE.format(
            company_name=state.company_name or "su empresa",
            total_footprint=total_footprint,
            per_employee=per_employee,
            score=sustainability_score,
            category=category,
            breakdown=breakdown_formatted,
            recommendations=recommendations_formatted
        )
        
        # Guardar resultados en el estado
        carbon_footprint = total_footprint
        carbon_per_employee = per_employee
        footprint_breakdown = breakdown
        
        # Marcar la conversación como terminada
        conversation_finished = True
        
        logger.info(f"Cálculo completado. Huella total: {total_footprint:.2f} ton CO₂e, Score: {sustainability_score}/100")
        
    except Exception as e:
        logger.error(f"Error durante el cálculo de huella de carbono: {e}", exc_info=True)
        response_message = f"""Lo siento, ha ocurrido un error durante el cálculo de la huella de carbono. 
Por favor, verifica que todos los datos ingresados sean correctos e intenta nuevamente.
Error: {str(e)}"""
        carbon_footprint = None
        carbon_per_employee = None
        footprint_breakdown = {}
        sustainability_score = None
        conversation_finished = True
    
    return {
        "carbon_footprint": carbon_footprint,
        "carbon_per_employee": carbon_per_employee,
        "footprint_breakdown": footprint_breakdown,
        "sustainability_score": sustainability_score,
        "messages": current_messages + [response_message],
        "current_task": next_task,
        "conversation_finished": conversation_finished,
        "last_user_intent": None,
        "user_input": None
    }

# --- Nodos de Manejo General (a revisar/adaptar) ---
# ... (Podríamos tener un nodo 'final_node' si quisiéramos hacer algo más al final)

# --- Asegurarse que los nodos antiguos irrelevantes estén eliminados o comentados ---
# def process_user_input_node(...): (Eliminado/Comentado)
# def ask_credit_type_node(...): (Eliminado/Comentado)
# def process_credit_type_node(...): (Eliminado/Comentado)
# ... etc ...