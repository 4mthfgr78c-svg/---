from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_worker_keyboard():
    buttons = [
        [KeyboardButton(text="📋 Мои смены")],
        [KeyboardButton(text="🧴 Заказать моющие")],
        [KeyboardButton(text="✅ Завершить текущую смену")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def main_manager_keyboard():
    buttons = [
        [KeyboardButton(text="🏢 Создать объект")],
        [KeyboardButton(text="📅 Назначить смену")],
        [KeyboardButton(text="📦 Заказы моющих")],
        [KeyboardButton(text="📊 Журнал смен (все)")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def shifts_inline(shifts):
    """shifts: list of (shift_id, object_name, start_time, end_time, status)"""
    kb = []
    for s in shifts:
        shift_id, obj_name, start, end, status, actual_start, actual_end = s
        # статус scheduled -> кнопка "Начать"
        if status == "scheduled":
            text = f"🚀 {obj_name} ({start.strftime('%d.%m %H:%M')})"
            kb.append([InlineKeyboardButton(text=text, callback_data=f"start_shift_{shift_id}")])
        # можно также показать завершённые, но без кнопок
    return InlineKeyboardMarkup(inline_keyboard=kb)

def orders_inline(orders):
    """orders: list of (order_id, text, created_at, full_name)"""
    kb = []
    for order_id, text, created_at, name in orders:
        short = text[:30] + "..." if len(text) > 30 else text
        kb.append([InlineKeyboardButton(f"✅ {name}: {short}", callback_data=f"process_order_{order_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)