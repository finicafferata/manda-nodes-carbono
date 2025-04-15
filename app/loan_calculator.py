import numpy_financial as npf
import numpy as np 
from typing import Optional, List, Dict, Any, Tuple
import logging 

logger = logging.getLogger(__name__) 

# Ahora recibe la lista de ProductRule (que incluye credit_type)
def calculate_loan_options(requested_amount: float, rules: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], bool]:
    """
    Calcula las opciones de préstamo. Ahora incluye 'credit_type' en la salida.
    Devuelve una tupla: (lista_de_opciones_validas, hubo_errores_de_calculo).
    """
    valid_options = []
    calculation_error_flag = False 

    if not rules or requested_amount is None:
        return [], calculation_error_flag

    logger.info(f"Calculando opciones para ${requested_amount:,.2f} con {len(rules)} reglas.")

    for rule in rules:
        rule_id = rule.get('product_id', 'N/A')
        try:
            min_amount = rule.get("min_amount", 0)
            max_amount = rule.get("max_amount", float('inf'))

            if not (min_amount <= requested_amount <= max_amount):
                continue # Saltar si monto no aplica

            # --- Extraer datos requeridos de la regla ---
            try:
                # ---> INCLUIR credit_type <---
                credit_type = rule.get("credit_type") # Puede ser None si no está definido
                annual_rate = float(rule["annual_rate"]) 
                num_installments = int(rule["num_installments"]) 
            except (KeyError, ValueError) as e:
                logger.error(f"Regla '{rule_id}' inválida/incompleta ({e}).", exc_info=True)
                calculation_error_flag = True
                continue

            # --- Cálculo de cuota ---
            try:
                monthly_rate = annual_rate / 12
                if monthly_rate <= -1: raise ValueError("Tasa inválida")
                monthly_payment_np = -npf.pmt(rate=monthly_rate, nper=num_installments, pv=requested_amount)
                if not np.isfinite(monthly_payment_np): raise ValueError("Resultado no finito")
                monthly_payment = float(round(monthly_payment_np, 2)) # Convertir a float
                total_amount = float(round(monthly_payment * num_installments, 2)) # Convertir a float
            except Exception as e:
                logger.error(f"Error calc cuota regla '{rule_id}': {e}", exc_info=True)
                calculation_error_flag = True 
                continue 

            # --- Añadir opción válida ---
            logger.info(f"Regla '{rule_id}' ({credit_type}) aplica. Cuota: {monthly_payment:.2f}")
            option_details = {
                "product_id": rule_id,
                # ---> AÑADIR credit_type <---
                "credit_type": credit_type, 
                "requested_amount": float(requested_amount), # Asegurar float
                "installment_amount": monthly_payment,
                "num_installments": num_installments,
                "total_amount": total_amount,
                "annual_rate": annual_rate
            }
            valid_options.append(option_details)

        except Exception as outer_e:
            logger.error(f"Error procesando regla '{rule_id}': {outer_e}", exc_info=True)
            calculation_error_flag = True
            continue

    if calculation_error_flag: logger.warning(f"Opciones={len(valid_options)}, errores ocurrieron.")
    else: logger.info(f"Opciones encontradas={len(valid_options)}, sin errores calc.")

    return valid_options, calculation_error_flag