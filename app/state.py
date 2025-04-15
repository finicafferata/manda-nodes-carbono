from typing import Dict, Optional, List, Any, Literal
# Importar ConfigDict si quieres usarlo explícitamente, aunque no es estrictamente necesario
# from pydantic import BaseModel, Field, ConfigDict 
from pydantic import BaseModel, Field
import uuid

# Tareas para el flujo de recolección de datos de huella de carbono
TaskStateType = Literal[
    # Datos básicos
    "esperando_nombre_empresa",
    "esperando_nombre_responsable",
    "esperando_cantidad_empleados",
    # Consumo energético
    "esperando_consumo_luz",          # Cambio: ahora en kWh, no en dinero
    "esperando_tipo_combustible",     # Nuevo: tipo de combustible principal
    "esperando_consumo_combustible",  # Cambio: en litros/m³, no en dinero
    "esperando_consumo_gas",          # Cambio: en m³, no en dinero
    # Transporte
    "esperando_distancia_empleados",  # Nuevo: km promedio diarios
    "esperando_distribucion_transporte", # Nuevo: % por tipo de transporte
    # Residuos
    "esperando_cantidad_residuos",    # Nuevo: kg mensuales
    "esperando_porcentaje_reciclaje", # Nuevo: % reciclado
    # Agua y papel
    "esperando_consumo_agua",         # Nuevo: m³ mensuales
    "esperando_consumo_papel",        # Nuevo: kg mensuales
    # Infraestructura
    "esperando_metros_oficina",       # Nuevo: m² de oficina
    "esperando_tipo_climatizacion",   # Nuevo: sistema de climatización
    # Viajes
    "esperando_km_avion",             # Nuevo: km en avión al mes
    "esperando_km_terrestres",        # Nuevo: km en tren/bus al mes
    # Fin del proceso
    "calculando_huella",              # Nuevo: estado de cálculo
    "mostrando_resultados",           # Nuevo: estado de visualización
    "revisando_datos",                # Opcional: resumen de datos recolectados
    "finalizando",                    # Final de la conversación
    None                              # Estado inicial
]

# Intenciones del usuario (mantenidas de la versión anterior)
IntentType = Literal[
    "respuesta_esperada",
    "pregunta_general",
    "saludo_despedida",
    "corregir_dato",
    "incomprensible",
    None
]

# Tipo de combustible principal
FuelType = Literal[
    "gasolina",
    "diesel",
    "gas_natural",
    "electricidad",
    "ninguno",
    None
]

# Tipo de climatización
ClimateControlType = Literal[
    "aire_acondicionado",
    "calefaccion_gas",
    "calefaccion_electrica",
    "bomba_calor",
    "natural",  # Sin climatización artificial
    None
]

class GraphState(BaseModel):
    """Estado para la conversación de recolección de datos de huella de carbono empresarial."""
    
    interaction_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    messages: list[str] = Field(default_factory=list)
    user_input: Optional[str] = None

    # --- Campos Nuevos para Datos de Empresa ---
    company_name: Optional[str] = None
    responsible_name: Optional[str] = None
    employee_count: Optional[int] = None # Usamos int para cantidad

    # --- Consumo Energético ---
    electricity_kwh: Optional[float] = None     # Consumo mensual en kWh 
    fuel_type: FuelType = None                  # Tipo de combustible principal
    fuel_consumption: Optional[float] = None    # Litros o m³ mensuales
    gas_consumption: Optional[float] = None     # m³ mensuales

    # --- Transporte ---
    employee_commute_distance: Optional[float] = None  # Km promedio diario por empleado
    transport_pct_car: Optional[int] = None            # % en auto particular
    transport_pct_public: Optional[int] = None         # % en transporte público
    transport_pct_green: Optional[int] = None          # % en bici/caminando
    
    # --- Residuos ---
    waste_kg: Optional[float] = None            # Kg residuos mensuales
    recycle_pct: Optional[int] = None           # % reciclado (0-100)
    
    # --- Agua y Papel ---
    water_consumption: Optional[float] = None   # m³ mensuales
    paper_consumption: Optional[float] = None   # kg mensuales
    
    # --- Infraestructura ---
    office_sqm: Optional[float] = None          # Metros cuadrados
    climate_control: ClimateControlType = None  # Tipo climatización
    
    # --- Viajes ---
    air_travel_km: Optional[float] = None       # Km en avión mensuales
    ground_travel_km: Optional[float] = None    # Km en tren/bus mensuales
    
    # --- Resultados del Cálculo ---
    carbon_footprint: Optional[float] = None    # Toneladas CO₂e totales
    carbon_per_employee: Optional[float] = None # Toneladas CO₂e por empleado
    sustainability_score: Optional[int] = None  # Puntaje 0-100
    footprint_breakdown: Dict[str, float] = Field(default_factory=dict)  # Desglose por categoría

    # --- Campos de Control de Flujo ---
    current_task: TaskStateType = None
    previous_task: Optional[TaskStateType] = None # Útil para volver atrás o corregir
    last_user_intent: IntentType = None
    conversation_finished: bool = False

    def add_message(self, message: str): 
        """Añade un mensaje al historial."""
        self.messages.append(message)
        
    # --- CORRECCIÓN AQUÍ ---
    # Reemplazar 'class Config:' con 'model_config' como diccionario
    model_config = {
        "arbitrary_types_allowed": True # Mantenido por si se añaden tipos complejos después
        # "extra": "allow" # Podrías necesitar "allow" o "ignore" si hay datos inesperados
    }
    # --- FIN CORRECCIÓN ---