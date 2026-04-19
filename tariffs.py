# tariffs.py — актуальные цены студии

BASE_PRICE_PER_HOUR = 1110
PRICE_3H = 2990
PRICE_5H = 4999
PRICE_10H = 9799
ENGINEER_PRICE_PER_HOUR = 400

def calculate_cost(duration: float, sound_engineer: bool = False) -> int:
    """Расчёт стоимости по пакетам"""
    if duration == 3.0:
        cost = PRICE_3H
    elif duration == 5.0:
        cost = PRICE_5H
    elif duration == 10.0:
        cost = PRICE_10H
    else:
        cost = int(duration * BASE_PRICE_PER_HOUR)
    
    if sound_engineer:
        cost += int(duration * ENGINEER_PRICE_PER_HOUR)
    
    return cost

def calculate_prepayment(full_cost: int) -> int:
    """10% предоплата"""
    return int(full_cost * 0.10)

def get_duration_text(duration: float) -> str:
    """Правильное склонение часов"""
    if duration == 1:
        return "1 час"
    elif duration in (2, 3, 4):
        return f"{int(duration)} часа"
    else:
        return f"{int(duration)} часов"