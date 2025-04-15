# tests/test_nodes_conversation.py
import pytest
import json
from unittest.mock import MagicMock # Alternativa a mocker si se prefiere

# Importar Clases y Nodos a probar (¡Usar rutas absolutas desde la raíz!)
# Asumiendo que ejecutas pytest desde la raíz del proyecto.
from app.state import GraphState, TaskStateType 
from app.nodes.conversation import process_user_input_node, AMOUNT_ERROR_MESSAGE, AMOUNT_INVALID_MESSAGE, PROCESSING_INPUT_MESSAGE

# --- Fixture para Simular Reglas (Opcional, pero útil) ---
# Se puede poner en conftest.py si se usa en más archivos
@pytest.fixture
def mock_rules():
    """Devuelve un conjunto de reglas simuladas para las pruebas."""
    return [
        {"product_id": "TEST_1", "credit_type": "consumo", "min_amount": 1000.0, "max_amount": 50000.0, "annual_rate": 0.8, "num_installments": 12},
        {"product_id": "TEST_2", "credit_type": "prendario", "min_amount": 30000.0, "max_amount": 100000.0, "annual_rate": 0.7, "num_installments": 36}
    ]

# --- Pruebas para process_user_input_node ---

def test_process_user_input_valid_amount_no_purpose(mocker, mock_rules):
    """Prueba input válido solo con monto, sin propósito explícito."""
    # 1. Configurar Mocks
    # Mockear la llamada a Gemini para extracción de monto/propósito
    mocker.patch(
        # Mockear donde se llama (en el módulo conversation)
        'app.nodes.conversation.call_gemini', 
        # Gemini debería devolver un JSON con monto ok, propósito null
        return_value='{"monto": 45000, "proposito": null}' 
    )
    # Mockear la carga de reglas para la validación de rango
    mocker.patch(
        'app.nodes.conversation.load_mandaflow_rules',
        return_value=mock_rules # Usar las reglas mockeadas
    )

    # 2. Preparar Estado Inicial
    initial_state = GraphState(
        user_input="necesito 45000", # Input del usuario
        current_task="esperando_monto"
    )

    # 3. Ejecutar Nodo
    result_update = process_user_input_node(initial_state)

    # 4. Verificar Resultados (Aserciones)
    assert result_update["requested_amount"] == 45000.0
    assert result_update["credit_type_purpose"] is None # No se extrajo propósito
    assert result_update["is_amount_within_range"] is True # 45000 está en el rango [1000, 100000] de mock_rules
    assert result_update["current_task"] is None # Pasa a la siguiente fase (decidida por condición)
    assert result_update["user_input"] is None # El input debe limpiarse
    assert result_update["last_user_intent"] is None # La intención debe limpiarse
    # Verificar que el mensaje de procesamiento se añadió (asumiendo que no hubo error)
    assert PROCESSING_INPUT_MESSAGE in result_update["messages"]
    assert AMOUNT_ERROR_MESSAGE not in result_update["messages"]
    assert AMOUNT_INVALID_MESSAGE.split('{')[0] not in "".join(result_update["messages"]) # Verificar que NO está el msg de fuera de rango

def test_process_user_input_valid_amount_with_purpose(mocker, mock_rules):
    """Prueba input válido con monto y propósito (usando slang)."""
     # 1. Mocks
    mocker.patch('app.nodes.conversation.call_gemini', return_value='{"monto": 60000, "proposito": "prendario"}')
    mocker.patch('app.nodes.conversation.load_mandaflow_rules', return_value=mock_rules)

    # 2. Estado Inicial
    initial_state = GraphState(user_input="60 lucas para la chata", current_task="esperando_monto")

    # 3. Ejecutar
    result_update = process_user_input_node(initial_state)

    # 4. Aserciones
    assert result_update["requested_amount"] == 60000.0
    assert result_update["credit_type_purpose"] == "prendario" # Propósito extraído
    assert result_update["is_amount_within_range"] is True # 60000 está en [1000, 100000]
    assert result_update["current_task"] is None
    assert result_update["user_input"] is None
    assert PROCESSING_INPUT_MESSAGE in result_update["messages"]

def test_process_user_input_invalid_format(mocker):
    """Prueba input que no contiene un monto claro."""
     # 1. Mock (Gemini no puede extraer monto)
    mocker.patch('app.nodes.conversation.call_gemini', return_value='{"monto": null, "proposito": null}')
    # No necesitamos mockear load_mandaflow_rules porque no debería llegar a validar rango

    # 2. Estado Inicial
    initial_state = GraphState(user_input="quiero un credito", current_task="esperando_monto")

    # 3. Ejecutar
    result_update = process_user_input_node(initial_state)

    # 4. Aserciones (Estado de error)
    assert result_update["requested_amount"] is None
    assert result_update["credit_type_purpose"] is None
    assert result_update["is_amount_within_range"] is False
    assert result_update["current_task"] == "esperando_monto" # Debe seguir esperando
    assert result_update["user_input"] is None
    # Verificar mensaje de error específico
    assert AMOUNT_ERROR_MESSAGE in result_update["messages"]
    # Asegurarse que NO añadió el de procesamiento
    assert PROCESSING_INPUT_MESSAGE not in result_update["messages"] 

def test_process_user_input_amount_out_of_range(mocker, mock_rules):
    """Prueba input con monto válido pero fuera del rango global."""
    # 1. Mocks
    mocker.patch('app.nodes.conversation.call_gemini', return_value='{"monto": 200000, "proposito": "hipotecario"}')
    mocker.patch('app.nodes.conversation.load_mandaflow_rules', return_value=mock_rules) # Rango es [1000, 100000]

    # 2. Estado Inicial
    initial_state = GraphState(user_input="200000 para mi casa", current_task="esperando_monto")

    # 3. Ejecutar
    result_update = process_user_input_node(initial_state)

    # 4. Aserciones
    assert result_update["requested_amount"] == 200000.0
    assert result_update["credit_type_purpose"] == "hipotecario" # Aún extrae el propósito
    assert result_update["is_amount_within_range"] is False # Fuera de rango
    # ---> ¡IMPORTANTE! La tarea debe ser esperar la acción 1 o 2 <---
    assert result_update["current_task"] == "esperando_next_action" 
    assert result_update["user_input"] is None
    # Verificar que está el mensaje de monto inválido CON los límites
    assert AMOUNT_INVALID_MESSAGE.split('{')[0] in "".join(result_update["messages"]) # Chequear inicio del mensaje
    assert "1,000" in "".join(result_update["messages"]) # Verificar que incluyó límites del mock
    assert "100,000" in "".join(result_update["messages"]) 
    assert PROCESSING_INPUT_MESSAGE in result_update["messages"] # Añade procesamiento antes de error de rango

def test_process_user_input_empty_input():
    """Prueba con input vacío."""
    # 1. Mocks (No se necesitan mocks aquí, no llama a LLM ni reglas)
    
    # 2. Estado Inicial
    initial_state = GraphState(user_input="", current_task="esperando_monto")

    # 3. Ejecutar
    result_update = process_user_input_node(initial_state)

    # 4. Aserciones (Similar a formato inválido)
    assert result_update["requested_amount"] is None
    assert result_update["credit_type_purpose"] is None
    assert result_update["is_amount_within_range"] is False
    assert result_update["current_task"] == "esperando_monto"
    assert result_update["user_input"] is None
    assert AMOUNT_ERROR_MESSAGE in result_update["messages"]
    assert PROCESSING_INPUT_MESSAGE not in result_update["messages"]

# --- TODO: Añadir más pruebas para otros nodos (income, expenses, preference, etc.) ---
# ... (Aquí irían las pruebas definidas en HU S10.3 y S10.4) ...