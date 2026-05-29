from aiogram.fsm.state import State, StatesGroup

class CreateObject(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()

class AssignShift(StatesGroup):
    waiting_for_worker = State()
    waiting_for_object = State()
    waiting_for_start = State()
    waiting_for_end = State()

class SupplyOrder(StatesGroup):
    waiting_for_text = State()

class EditObject(StatesGroup):
    waiting_for_new_name = State()
    waiting_for_new_address = State()