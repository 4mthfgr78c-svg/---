from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ---- Постоянные меню с кнопкой "Главное меню" ----
def main_worker_keyboard():
    buttons = [
        [KeyboardButton(text="📋 Мои смены")],
        [KeyboardButton(text="🧴 Заказать моющие")],
        [KeyboardButton(text="✅ Завершить текущую смену")],
        [KeyboardButton(text="🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def main_manager_keyboard():
    buttons = [
        [KeyboardButton(text="🏢 Создать объект")],
        [KeyboardButton(text="📅 Назначить смену")],
        [KeyboardButton(text="📦 Заказы моющих")],
        [KeyboardButton(text="📊 Журнал смен (все)")],
        [KeyboardButton(text="📍 Состояние объектов")],
        [KeyboardButton(text="🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ---- Клавиатуры для выбора (инлайн) ----
def workers_inline(workers):
    """workers: list of (tg_id, full_name)"""
    kb = []
    for tg_id, name in workers:
        kb.append([InlineKeyboardButton(text=name, callback_data=f"worker_{tg_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def objects_inline(objects):
    """objects: list of (id, name, address)"""
    kb = []
    for obj_id, name, address in objects:
        kb.append([InlineKeyboardButton(text=name, callback_data=f"obj_{obj_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def shifts_inline(shifts):
    """shifts: list of (shift_id, object_name, start_time, end_time, status, ...)"""
    kb = []
    for s in shifts:
        shift_id, obj_name, start, end, status, actual_start, actual_end = s
        if status == "scheduled":
            text = f"🚀 {obj_name} ({start.strftime('%d.%m %H:%M')})"
            kb.append([InlineKeyboardButton(text=text, callback_data=f"start_shift_{shift_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def orders_inline(orders):
    """orders: list of (order_id, text, created_at, full_name)"""
    kb = []
    for order_id, text, created_at, name in orders:
        short = text[:30] + "..." if len(text) > 30 else text
        kb.append([InlineKeyboardButton(text=f"✅ {name}: {short}", callback_data=f"process_order_{order_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)