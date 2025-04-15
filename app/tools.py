from typing import Dict, Any
import numpy_financial as npf # pip install numpy-financial

# --- Sprint 1: Hardcoded Rules ---
PRODUCT_RULES = {
    "min_amount": 1000.0,
    "max_amount": 10000.0,
    "tna": 0.85,  # 85% Tasa Nominal Anual
    "installments": 12,
}
# --- ---

def calculate_simple_loan(requested_amount: float) -> Dict[str, Any]:
    """
    Calculates loan details based on hardcoded rules for Sprint 1.
    Returns a dictionary with calculation results and validity.
    """
    rules = PRODUCT_RULES
    is_valid = rules["min_amount"] <= requested_amount <= rules["max_amount"]
    
    result = {
        "requested_amount": requested_amount,
        "is_amount_valid": is_valid,
        "num_installments": rules["installments"],
        "tna": rules["tna"],
        "installment_amount": None, # Default to None
        "valid_range": (rules["min_amount"], rules["max_amount"])
    }

    if is_valid:
        try:
            # Calculate monthly rate from TNA
            monthly_rate = rules["tna"] / 12
            # Calculate installment amount using numpy-financial
            # npf.pmt(rate, nper, pv) - pv (present value) is negative
            installment = npf.pmt(monthly_rate, rules["installments"], -requested_amount)
            result["installment_amount"] = round(installment, 2)
        except Exception as e:
            print(f"Error during calculation: {e}") # Log error
            result["is_amount_valid"] = False # Mark as invalid if calc fails
            result["installment_amount"] = None

    return result