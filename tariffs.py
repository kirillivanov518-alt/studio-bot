# tariffs.py
BASE_PRICE_PER_HOUR = 1110
SPECIAL_3H_PRICE = 2990
ENGINEER_PRICE_PER_HOUR = 400

def calculate_cost(duration: float, sound_engineer: bool = False) -> int:
    if duration == 3.0:
        cost = SPECIAL_3H_PRICE
    else:
        cost = int(duration * BASE_PRICE_PER_HOUR)
    
    if sound_engineer:
        cost += int(duration * ENGINEER_PRICE_PER_HOUR)
    
    return cost

def calculate_prepayment(full_cost: int) -> int:
    return int(full_cost * 0.10)