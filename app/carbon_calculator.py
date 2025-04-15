"""
Módulo para calcular la huella de carbono empresarial.
Incluye factores de emisión y funciones de cálculo para diferentes categorías.
"""

from typing import Dict, Any, Optional
from .state import GraphState, FuelType, ClimateControlType
import logging

logger = logging.getLogger(__name__)

# --- Factores de Emisión (kg CO₂e) ---

# Electricidad (kg CO₂e por kWh) - Varía según país y matriz energética
ELECTRICITY_FACTORS = {
    "default": 0.385,     # Promedio global aproximado
    "argentina": 0.310,   # Factor para Argentina
    "mexico": 0.494,      # Factor para México
    "colombia": 0.199,    # Factor para Colombia (más renovable)
    "españa": 0.250,      # Factor para España
}

# Combustibles (kg CO₂e por litro o m³)
FUEL_FACTORS = {
    "gasolina": 2.31,     # kg CO₂e por litro
    "diesel": 2.68,       # kg CO₂e por litro
    "gas_natural": 2.07,  # kg CO₂e por m³
    "electricidad": 0.0,  # Contabilizado en electricidad
    "ninguno": 0.0
}

# Transporte (kg CO₂e por km por persona)
TRANSPORT_FACTORS = {
    "auto": 0.17,         # Emisión por km en auto privado
    "publico": 0.09,      # Emisión por km en transporte público
    "verde": 0.0          # Sin emisiones (bicicleta, caminar)
}

# Viajes (kg CO₂e por km)
TRAVEL_FACTORS = {
    "avion_corto": 0.158,  # Vuelos < 1500 km
    "avion_largo": 0.115,  # Vuelos > 1500 km (más eficientes por km)
    "tren": 0.035,         # Tren
    "bus": 0.068           # Autobús/Ómnibus
}

# Residuos (kg CO₂e por kg)
WASTE_FACTORS = {
    "vertedero": 0.586,    # Residuos a vertedero
    "reciclado": 0.058     # Residuos reciclados (menor, pero no cero)
}

# Agua (kg CO₂e por m³)
WATER_FACTOR = 0.344

# Papel (kg CO₂e por kg)
PAPER_FACTOR = 1.50

# Infraestructura (kg CO₂e por m² por año, convertido a mensual)
BUILDING_FACTOR = 7.5 / 12  # Emisiones por m² de oficina al mes

# --- Funciones de Cálculo ---

def calculate_carbon_footprint(state: GraphState, country: str = "default") -> Dict[str, Any]:
    """
    Calcula la huella de carbono total y por categoría.
    Devuelve un diccionario con los resultados.
    """
    # Diccionario para almacenar resultados
    results = {}
    
    # Seleccionar factor de electricidad según país
    electricity_factor = ELECTRICITY_FACTORS.get(country.lower(), ELECTRICITY_FACTORS["default"])
    
    # 1. Cálculo de emisiones por electricidad
    electricity_footprint = 0
    if state.electricity_kwh:
        electricity_footprint = state.electricity_kwh * electricity_factor
        logger.info(f"Huella eléctrica: {electricity_footprint:.2f} kg CO₂e")
    
    # 2. Cálculo de emisiones por combustible
    fuel_footprint = 0
    if state.fuel_type and state.fuel_consumption:
        fuel_factor = FUEL_FACTORS.get(state.fuel_type, 0)
        fuel_footprint = state.fuel_consumption * fuel_factor
        logger.info(f"Huella combustible ({state.fuel_type}): {fuel_footprint:.2f} kg CO₂e")
    
    # 3. Cálculo de emisiones por gas
    gas_footprint = 0
    if state.gas_consumption:
        gas_footprint = state.gas_consumption * FUEL_FACTORS["gas_natural"]
        logger.info(f"Huella gas: {gas_footprint:.2f} kg CO₂e")
    
    # 4. Cálculo de emisiones por transporte de empleados
    transport_footprint = 0
    if state.employee_count and state.employee_commute_distance:
        # Días laborables promedio al mes
        work_days = 22
        
        # Asegurar que tenemos porcentajes para las categorías (defaults conservadores)
        pct_car = state.transport_pct_car or 60
        pct_public = state.transport_pct_public or 30
        pct_green = state.transport_pct_green or 10
        
        # Emisiones diarias por categoría
        car_emissions = (state.employee_commute_distance * TRANSPORT_FACTORS["auto"] * 
                         state.employee_count * (pct_car / 100))
        public_emissions = (state.employee_commute_distance * TRANSPORT_FACTORS["publico"] * 
                            state.employee_count * (pct_public / 100))
        # Las emisiones "verdes" son cero
        
        # Emisiones mensuales (ida y vuelta)
        transport_footprint = (car_emissions + public_emissions) * work_days * 2
        logger.info(f"Huella transporte empleados: {transport_footprint:.2f} kg CO₂e")
    
    # 5. Cálculo de emisiones por residuos
    waste_footprint = 0
    if state.waste_kg:
        # Porcentaje enviado a vertedero vs reciclado
        pct_recycle = state.recycle_pct or 0
        pct_landfill = 100 - pct_recycle
        
        # Calcular emisiones
        waste_footprint = (state.waste_kg * (pct_landfill / 100) * WASTE_FACTORS["vertedero"] + 
                           state.waste_kg * (pct_recycle / 100) * WASTE_FACTORS["reciclado"])
        logger.info(f"Huella residuos: {waste_footprint:.2f} kg CO₂e")
    
    # 6. Cálculo de emisiones por agua
    water_footprint = 0
    if state.water_consumption:
        water_footprint = state.water_consumption * WATER_FACTOR
        logger.info(f"Huella agua: {water_footprint:.2f} kg CO₂e")
    
    # 7. Cálculo de emisiones por papel
    paper_footprint = 0
    if state.paper_consumption:
        paper_footprint = state.paper_consumption * PAPER_FACTOR
        logger.info(f"Huella papel: {paper_footprint:.2f} kg CO₂e")
    
    # 8. Cálculo de emisiones por infraestructura
    building_footprint = 0
    if state.office_sqm:
        building_footprint = state.office_sqm * BUILDING_FACTOR
        # Ajustar según el tipo de climatización
        if state.climate_control:
            adjustment = {
                "aire_acondicionado": 1.5,
                "calefaccion_gas": 1.3,
                "calefaccion_electrica": 1.2,
                "bomba_calor": 1.1,
                "natural": 0.8
            }.get(state.climate_control, 1.0)
            building_footprint *= adjustment
        logger.info(f"Huella infraestructura: {building_footprint:.2f} kg CO₂e")
    
    # 9. Cálculo de emisiones por viajes
    travel_footprint = 0
    # Simplificación: dividir viajes aéreos 50/50 entre cortos y largos
    if state.air_travel_km:
        air_short = state.air_travel_km * 0.5
        air_long = state.air_travel_km * 0.5
        air_footprint = (air_short * TRAVEL_FACTORS["avion_corto"] + 
                         air_long * TRAVEL_FACTORS["avion_largo"])
        travel_footprint += air_footprint
    
    # Simplificación: dividir viajes terrestres 50/50 entre tren y bus
    if state.ground_travel_km:
        train = state.ground_travel_km * 0.5
        bus = state.ground_travel_km * 0.5
        ground_footprint = (train * TRAVEL_FACTORS["tren"] + 
                            bus * TRAVEL_FACTORS["bus"])
        travel_footprint += ground_footprint
    
    logger.info(f"Huella viajes: {travel_footprint:.2f} kg CO₂e")
    
    # 10. Suma total de emisiones (kg CO₂e)
    total_footprint = (electricity_footprint + fuel_footprint + gas_footprint + 
                       transport_footprint + waste_footprint + water_footprint + 
                       paper_footprint + building_footprint + travel_footprint)
    
    # Convertir a toneladas
    total_footprint_tons = total_footprint / 1000
    
    # Huella por empleado
    per_employee = 0
    if state.employee_count and state.employee_count > 0:
        per_employee = total_footprint_tons / state.employee_count
    
    # Desglose por categoría
    footprint_breakdown = {
        "electricidad": electricity_footprint / 1000,
        "combustible": fuel_footprint / 1000,
        "gas": gas_footprint / 1000,
        "transporte_empleados": transport_footprint / 1000,
        "residuos": waste_footprint / 1000,
        "agua": water_footprint / 1000,
        "papel": paper_footprint / 1000,
        "infraestructura": building_footprint / 1000,
        "viajes": travel_footprint / 1000
    }
    
    # Cálculo de puntaje de sostenibilidad (0-100)
    # Valores de referencia para pequeñas empresas
    reference_per_employee = 3.5  # toneladas CO₂e por empleado al año (promedio)
    min_per_employee = 0.5       # muy bueno
    max_per_employee = 10.0      # muy malo
    
    # Normalizar la huella por empleado a un puntaje (más alto = mejor)
    # Inversamente proporcional: menor huella = mayor puntaje
    if per_employee > 0:
        # Convertir la huella mensual a anual para comparar con referencias
        annual_per_employee = per_employee * 12
        
        # Calcular puntaje normalizado
        if annual_per_employee <= min_per_employee:
            sustainability_score = 100
        elif annual_per_employee >= max_per_employee:
            sustainability_score = 0
        else:
            # Escala inversa: mayor huella = menor puntaje
            sustainability_score = int(100 * (max_per_employee - annual_per_employee) / 
                                       (max_per_employee - min_per_employee))
    else:
        sustainability_score = 50  # Valor por defecto si no hay datos suficientes
    
    # Empaquetar resultados
    results = {
        "total_footprint": total_footprint_tons,
        "per_employee": per_employee,
        "breakdown": footprint_breakdown,
        "sustainability_score": sustainability_score
    }
    
    logger.info(f"Huella total: {total_footprint_tons:.2f} toneladas CO₂e")
    logger.info(f"Huella por empleado: {per_employee:.2f} toneladas CO₂e")
    logger.info(f"Puntaje sostenibilidad: {sustainability_score}/100")
    
    return results

def get_score_category(score: int) -> str:
    """Devuelve la categoría de sostenibilidad según el puntaje."""
    if score >= 81:
        return "Excelente (muy baja huella)"
    elif score >= 61:
        return "Buena (baja huella)"
    elif score >= 41:
        return "Media"
    elif score >= 21:
        return "Regular (alta huella)"
    else:
        return "Deficiente (muy alta huella)"

def get_recommendations(state: GraphState, score: int) -> list[str]:
    """Genera recomendaciones personalizadas según los datos y el puntaje."""
    recommendations = []
    
    # Recomendaciones básicas según puntaje
    if score < 50:
        recommendations.append("Realizar una auditoría energética completa.")
    
    # Recomendaciones específicas según los datos
    
    # Electricidad
    if state.electricity_kwh and state.electricity_kwh > 300 * (state.employee_count or 1):
        recommendations.append("Optimizar el consumo eléctrico: cambiar a iluminación LED y equipos eficientes.")
    
    # Transporte
    if state.transport_pct_car and state.transport_pct_car > 60:
        recommendations.append("Implementar un programa de transporte compartido o subsidios para transporte público.")
    
    # Residuos
    if not state.recycle_pct or state.recycle_pct < 30:
        recommendations.append("Establecer un programa de reciclaje y reducción de residuos.")
    
    # Papel
    if state.paper_consumption and state.paper_consumption > 5 * (state.employee_count or 1):
        recommendations.append("Implementar una política de oficina sin papel y digitalizar procesos.")
    
    # Climatización
    if state.climate_control in ["aire_acondicionado", "calefaccion_electrica"]:
        recommendations.append("Mejorar el aislamiento térmico y regular la temperatura del edificio.")
    
    # Añadir recomendaciones generales si hay pocas específicas
    if len(recommendations) < 3:
        recommendations.append("Considerar la instalación de paneles solares u otras fuentes de energía renovable.")
        recommendations.append("Educar a los empleados sobre prácticas sostenibles en el trabajo y en casa.")
    
    return recommendations 