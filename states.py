from aiogram.fsm.state import State, StatesGroup
 
class BookingStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_duration = State()
    waiting_for_custom_duration = State()
    waiting_for_sound_engineer = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_comment = State()
    waiting_for_payment = State()