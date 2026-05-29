from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

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
        [KeyboardButton(text="✏️ Управление объектами")],
        [KeyboardButton(text="📅 Назначить смену")],
        [KeyboardButton(text="📦 Заказы моющих")],
        [KeyboardButton(text="📊 Журнал смен (все)")],
        [KeyboardButton(text="📍 Состояние объектов")],
        [KeyboardButton(text="🏠 Главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def workers_inline(workers):
    kb = []
    for tg_id, name in workers:
        kb.append([InlineKeyboardButton(text=name, callback_data=f"worker_{tg_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def objects_inline(objects):
    kb = []
    for obj_id, name, address in objects:
        kb.append([InlineKeyboardButton(text=name, callback_data=f"obj_{obj_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def manage_objects_inline(objects):
    """Клавиатура для управления объектами: редактировать и удалять"""
    kb = []
    for obj_id, name, address in objects:
        kb.append([
            InlineKeyboardButton(text=f"✏️ {name}", callback_data=f"edit_obj_{obj_id}"),
            InlineKeyboardButton(text=f"🗑 Удалить", callback_data=f"delete_obj_{obj_id}")
        ])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def shifts_inline(shifts):
    kb = []
    for s in shifts:
        shift_id, obj_name, start, end, status, actual_start, actual_end = s
        if status == "scheduled":
            text = f"🚀 {obj_name} ({start.strftime('%d.%m %H:%M')})"
            kb.append([InlineKeyboardButton(text=text, callback_data=f"start_shift_{shift_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def orders_inline(orders):
    kb = []
    for order_id, text, created_at, name in orders:
        short = text[:30] + "..." if len(text) > 30 else text
        kb.append([InlineKeyboardButton(text=f"✅ {name}: {short}", callback_data=f"process_order_{order_id}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def confirm_delete_inline(obj_id, obj_name):
    """Подтверждение удаления объекта"""
    kb = [
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_del_{obj_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)