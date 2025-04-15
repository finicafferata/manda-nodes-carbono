import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import logging
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Configuración
# API_KEY = os.environ.get('GOOGLE_API_KEY')  # Comentado - Ahora se obtiene dentro de configure_gemini_client
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-1.5-flash-001")

_gemini_model = None

def configure_gemini_client():
    """Configura el cliente de google-generativeai con la API Key."""
    global _gemini_model
    
    # Obtener la API key en el momento de la configuración, no cuando se importa
    API_KEY = os.environ.get('GOOGLE_API_KEY')
    
    if not API_KEY:
        logger.error("La variable de entorno GOOGLE_API_KEY no está configurada.")
        _gemini_model = None
        return

    try:
        logger.info(f"Configurando cliente Gemini con API Key...")
        genai.configure(api_key=API_KEY)
        _gemini_model = genai.GenerativeModel(MODEL_NAME)
        logger.info(f"Modelo Gemini '{MODEL_NAME}' listo para usar (API Key).")
        try:
            # Prueba rápida (en un try/except para más seguridad)
            _gemini_model.generate_content("test") 
            logger.info("Llamada de prueba a Gemini (API Key) exitosa.")
        except Exception as test_e:
            logger.error(f"La prueba de Gemini falló: {test_e}. La clave podría ser inválida.")
            _gemini_model = None
    except Exception as e:
        logger.error(f"Error al configurar el cliente Gemini: {e}", exc_info=True)
        _gemini_model = None

def call_gemini(prompt: str, temperature: float = 0.2, max_output_tokens: int = 100) -> Optional[str]:
    """Llama al modelo Gemini configurado."""
    global _gemini_model
    if not _gemini_model:
        logger.error("El modelo Gemini (API Key) no está configurado.")
        return None

    logger.info(f"Llamando a Gemini (API Key) con prompt: {prompt[:150]}...") # Log más largo

    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        # ... (otras categorías)
    }
    generation_config = {
        "temperature": temperature,
        "top_p": 0.8,
        "top_k": 40,
        "max_output_tokens": max_output_tokens,
    }

    try:
        response = _gemini_model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
        if response.text:
            result_text = response.text.strip()
            logger.info(f"Respuesta de Gemini (API Key) recibida: '{result_text}'")
            return result_text
        else:
            block_reason = None
            try:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                     block_reason = response.prompt_feedback.block_reason
            except Exception: pass
            logger.warning(f"Respuesta de Gemini (API Key) vacía o bloqueada. Block reason: {block_reason}")
            return None
    except Exception as e:
        logger.error(f"Error durante la llamada a la API de Gemini (API Key): {e}", exc_info=True)
        return None

# --- Nueva Función Sprint 6 ---
def classify_intent(user_input: str, expected_task: Optional[str]) -> Optional[str]:
    """
    Clasifica la intención del usuario usando Gemini.
    """
    if not user_input: return "incomprensible"

    possible_intents = ["respuesta_esperada", "consulta_limite", "pregunta_general", "saludo_despedida", "cambiar_monto", "incomprensible"]

    # --- Prompt Mejorado ---
    prompt = f"Contexto: El asistente de crédito espera información sobre '{expected_task if expected_task else 'inicio'}'.\n"
    prompt += f"Entrada del Usuario: '{user_input}'\n\n"
    prompt += "Tarea: Clasifica la intención principal del usuario.\n"
    prompt += "Definiciones de Intenciones:\n"
    prompt += "- respuesta_esperada: Proporciona información directamente relevante a la fase actual (ej. si se espera monto, da un número; si se espera flujo, describe cuándo paga; si se espera preferencia, dice A/B o similar; si se espera acción final, dice 1/2).\n"
    prompt += "- consulta_limite: Pregunta específicamente sobre el monto máximo o mínimo.\n"
    prompt += "- pregunta_general: Hace otra pregunta sobre el crédito, tasas, proceso, etc.\n"
    prompt += "- saludo_despedida: Es un saludo (hola), despedida (adiós) o agradecimiento (gracias).\n"
    prompt += "- cambiar_monto: Indica explícitamente querer consultar un monto diferente (SOLO si la fase actual es 'esperando_next_action').\n"
    prompt += "- incomprensible: No encaja en ninguna categoría o es irrelevante.\n\n"
    prompt += "Ejemplos:\n"
    prompt += "* Fase: esperando_flujo, Usuario: 'los días 15' -> respuesta_esperada\n"
    prompt += "* Fase: esperando_flujo, Usuario: 'cuando puedo' -> respuesta_esperada\n"
    prompt += "* Fase: esperando_flujo, Usuario: 'cuanto es la tasa?' -> pregunta_general\n"
    prompt += "* Fase: esperando_monto, Usuario: 'que es tna?' -> pregunta_general\n"
    prompt += "* Fase: esperando_monto, Usuario: '10000' -> respuesta_esperada\n"
    prompt += "* Fase: esperando_preferencia, Usuario: 'la A' -> respuesta_esperada\n"
    prompt += "* Fase: esperando_preferencia, Usuario: 'depende...' -> incomprensible\n"
    prompt += "* Fase: esperando_next_action, Usuario: 'cual es el maximo' -> consulta_limite\n"
    prompt += "* Fase: esperando_next_action, Usuario: 'quiero otro monto' -> cambiar_monto\n\n"
    prompt += "IMPORTANTE: Responde únicamente con UNA de las siguientes etiquetas:\n"
    prompt += f"{', '.join(possible_intents)}"
    # --- Fin Prompt Mejorado ---

    response = call_gemini(prompt, temperature=0.1, max_output_tokens=20)

    if response and response in possible_intents:
        logger.info(f"Intención clasificada como: '{response}' para input '{user_input}' (esperaba: {expected_task})")
        return response
    else:
        logger.warning(f"No se pudo clasificar la intención o la respuesta no fue válida: '{response}'. Se asume 'incomprensible'.")
        return "incomprensible"

# Bloque de prueba
if __name__ == "__main__":
    print("Probando configuración de cliente Gemini (API Key)...")
    configure_gemini_client()
    if _gemini_model:
        print("\nProbando clasificación de intención...")
        test_inputs = [
            ("5000", "esperando_monto"),
            ("cuanto es lo maximo?", "esperando_monto"),
            ("hola", "esperando_monto"),
            ("15 del mes", "esperando_flujo"),
            ("y si pido 2000?", "esperando_flujo"),
            ("la B", "esperando_preferencia"),
            ("gracias", "esperando_preferencia"),
            ("1", "esperando_next_action"),
            ("quiero cambiar el monto", "esperando_next_action"),
            ("blablabla", "esperando_monto"),
        ]
        for text, task in test_inputs:
            intent = classify_intent(text, task)
            print(f"- Input: '{text}' (Esperaba: {task}) -> Intención: {intent}")
    else:
        print("La configuración del cliente Gemini (API Key) falló.")