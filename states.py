from aiogram.fsm.state import State, StatesGroup

class BookingStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_duration = State()
    waiting_for_sound_engineer = State()
    waiting_for_payment = State()   # подтверждение перед оплатой