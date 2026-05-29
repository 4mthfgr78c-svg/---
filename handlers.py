import re
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.enums.parse_mode import ParseMode

from config import BOT_TOKEN, MANAGER_IDS
from database import *
from keyboards import *
from states import *

router = Router()

# -------------------- Регистрация --------------------
@router.message(Command("start"))
async def cmd_start(message: Message):
    tg_id = message.from_user.id
    register_user(tg_id, message.from_user.username, message.from_user.full_name)
    if is_manager(tg_id):
        await message.answer("👋 Здравствуйте, менеджер! Используйте кнопки ниже.", reply_markup=main_manager_keyboard())
    else:
        await message.answer("👋 Добро пожаловать, уборщица! Используйте кнопки для работы.", reply_markup=main_worker_keyboard())

# -------------------- Менеджер: создание объекта --------------------
@router.message(F.text == "🏢 Создать объект")
async def create_object_start(message: Message, state: FSMContext):
    if not is_manager(message.from_user.id):
        return
    await message.answer("Введите название объекта:")
    await state.set_state(CreateObject.waiting_for_name)

@router.message(CreateObject.waiting_for_name)
async def create_object_name(message: Message, state: FSMContext):
    await state.update_data(obj_name=message.text)
    await message.answer("Введите адрес объекта:")
    await state.set_state(CreateObject.waiting_for_address)

@router.message(CreateObject.waiting_for_address)
async def create_object_address(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data["obj_name"]
    address = message.text
    add_object(name, address, message.from_user.id)
    await message.answer(f"✅ Объект «{name}» добавлен.", reply_markup=main_manager_keyboard())
    await state.clear()

# -------------------- Менеджер: назначение смены --------------------
@router.message(F.text == "📅 Назначить смену")
async def assign_shift_start(message: Message, state: FSMContext):
    if not is_manager(message.from_user.id):
        return
    await message.answer("Введите Telegram ID уборщицы (число):")
    await state.set_state(AssignShift.waiting_for_worker)

@router.message(AssignShift.waiting_for_worker)
async def assign_shift_worker(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Ошибка: ID должен быть числом. Попробуйте снова.")
        return
    worker_id = int(message.text)
    # проверим, существует ли пользователь
    with get_connection() as conn:
        row = conn.execute("SELECT tg_id FROM users WHERE tg_id = ?", (worker_id,)).fetchone()
        if not row:
            await message.answer("Пользователь с таким ID не найден. Сначала уборщица должна запустить /start.")
            return
    await state.update_data(worker_id=worker_id)
    objects = get_objects()
    if not objects:
        await message.answer("Сначала создайте хотя бы один объект командой «Создать объект».")
        await state.clear()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=name, callback_data=f"obj_{obj_id}")] for obj_id, name, _ in objects
    ])
    await message.answer("Выберите объект:", reply_markup=kb)
    await state.set_state(AssignShift.waiting_for_object)

@router.callback_query(AssignShift.waiting_for_object, F.data.startswith("obj_"))
async def assign_shift_object(call: CallbackQuery, state: FSMContext):
    object_id = int(call.data.split("_")[1])
    await state.update_data(object_id=object_id)
    await call.message.edit_text("Введите дату и время начала смены в формате: ГГГГ-ММ-ДД ЧЧ:ММ (например, 2025-06-01 10:00)")
    await state.set_state(AssignShift.waiting_for_start)
    await call.answer()

@router.message(AssignShift.waiting_for_start)
async def assign_shift_start_time(message: Message, state: FSMContext):
    try:
        start_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("Неверный формат. Используйте ГГГГ-ММ-ДД ЧЧ:ММ")
        return
    await state.update_data(start_time=start_time)
    await message.answer("Введите дату и время окончания смены (аналогичный формат):")
    await state.set_state(AssignShift.waiting_for_end)

@router.message(AssignShift.waiting_for_end)
async def assign_shift_end_time(message: Message, state: FSMContext):
    try:
        end_time = datetime.strptime(message.text, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("Неверный формат. Используйте ГГГГ-ММ-ДД ЧЧ:ММ")
        return
    data = await state.get_data()
    if end_time <= data["start_time"]:
        await message.answer("Окончание смены должно быть позже начала.")
        return
    add_shift(data["worker_id"], data["object_id"], data["start_time"], end_time)
    await message.answer("✅ Смена назначена.", reply_markup=main_manager_keyboard())
    await state.clear()

# -------------------- Уборщица: мои смены --------------------
@router.message(F.text == "📋 Мои смены")
async def my_shifts(message: Message):
    tg_id = message.from_user.id
    shifts = get_worker_shifts(tg_id)
    if not shifts:
        await message.answer("У вас нет назначенных смен.")
        return
    text = "📅 Ваши смены:\n\n"
    for s in shifts:
        shift_id, obj_name, start, end, status, actual_start, actual_end = s
        status_emoji = "⏳" if status == "scheduled" else "🔄" if status == "in_progress" else "✅"
        text += f"{status_emoji} {obj_name}\n   {start.strftime('%d.%m %H:%M')} – {end.strftime('%H:%M')}\n"
        if status == "in_progress" and actual_start:
            text += f"   Начало в {actual_start.strftime('%H:%M')}\n"
        text += "\n"
    await message.answer(text, reply_markup=shifts_inline(shifts))

# Уборщица начинает смену по инлайн-кнопке
@router.callback_query(F.data.startswith("start_shift_"))
async def start_shift_callback(call: CallbackQuery):
    shift_id = int(call.data.split("_")[2])
    # проверим, что смена принадлежит этому пользователю
    with get_connection() as conn:
        row = conn.execute("SELECT worker_tg_id, status FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        if not row or row[0] != call.from_user.id:
            await call.answer("Это не ваша смена!", show_alert=True)
            return
        if row[1] != "scheduled":
            await call.answer("Смена уже начата или завершена.", show_alert=True)
            return
    start_shift(shift_id, datetime.now())
    await call.message.edit_text("🚀 Смена начата! Когда закончите, нажмите «Завершить текущую смену» в меню.")
    await call.answer()

# Завершить текущую смену (с возможностью фото)
@router.message(F.text == "✅ Завершить текущую смену")
async def finish_shift_prompt(message: Message):
    active = get_active_shift(message.from_user.id)
    if not active:
        await message.answer("У вас нет активной смены.")
        return
    await message.answer("Приложите фото после уборки (необязательно) или просто напишите «пропустить» для завершения без фото.")

@router.message(F.text == "пропустить")
async def finish_shift_no_photo(message: Message):
    active = get_active_shift(message.from_user.id)
    if not active:
        await message.answer("Нет активной смены.")
        return
    shift_id, obj_id, start_time, end_time = active
    end_shift(shift_id, datetime.now())
    await message.answer("✅ Смена завершена (без фото). Спасибо за работу!", reply_markup=main_worker_keyboard())

@router.message(F.photo)
async def finish_shift_with_photo(message: Message):
    active = get_active_shift(message.from_user.id)
    if not active:
        await message.answer("Нет активной смены.")
        return
    shift_id, obj_id, start_time, end_time = active
    photo_file_id = message.photo[-1].file_id
    end_shift(shift_id, datetime.now(), photo_file_id)
    await message.answer("✅ Смена завершена, фото сохранено. Спасибо!", reply_markup=main_worker_keyboard())

# -------------------- Заказ моющих средств --------------------
@router.message(F.text == "🧴 Заказать моющие")
async def order_supply(message: Message, state: FSMContext):
    await message.answer("Напишите, что нужно заказать (название, количество, примечания):")
    await state.set_state(SupplyOrder.waiting_for_text)

@router.message(SupplyOrder.waiting_for_text)
async def order_supply_text(message: Message, state: FSMContext):
    add_supply_order(message.from_user.id, message.text)
    await message.answer("✅ Заказ отправлен менеджеру.", reply_markup=main_worker_keyboard())
    await state.clear()
    # уведомить всех менеджеров
    from config import MANAGER_IDS
    for mgr in MANAGER_IDS:
        try:
            await message.bot.send_message(mgr, f"📦 Новый заказ моющих от {message.from_user.full_name}:\n{message.text}")
        except:
            pass

# -------------------- Менеджер: просмотр заказов --------------------
@router.message(F.text == "📦 Заказы моющих")
async def view_orders(message: Message):
    if not is_manager(message.from_user.id):
        return
    orders = get_new_orders()
    if not orders:
        await message.answer("Нет новых заказов.")
        return
    await message.answer("Новые заказы (нажмите, чтобы отметить как обработанный):", reply_markup=orders_inline(orders))

@router.callback_query(F.data.startswith("process_order_"))
async def process_order_callback(call: CallbackQuery):
    order_id = int(call.data.split("_")[2])
    mark_order_processed(order_id, call.from_user.id)
    await call.message.edit_text(f"✅ Заказ №{order_id} отмечен как обработанный.")
    await call.answer()

# -------------------- Журнал смен для менеджера --------------------
@router.message(F.text == "📊 Журнал смен (все)")
async def all_shifts_log(message: Message):
    if not is_manager(message.from_user.id):
        return
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT s.id, u.full_name, o.name, s.start_time, s.end_time, s.actual_start, s.actual_end, s.status
            FROM shifts s
            JOIN users u ON s.worker_tg_id = u.tg_id
            JOIN objects o ON s.object_id = o.id
            ORDER BY s.start_time DESC LIMIT 50
        """).fetchall()
    if not rows:
        await message.answer("Нет ни одной смены.")
        return
    text = "📋 Последние 50 смен:\n\n"
    for r in rows:
        text += f"{r[1]} — {r[2]}\n  План: {r[3].strftime('%d.%m %H:%M')} - {r[4].strftime('%H:%M')}\n"
        if r[5]:
            text += f"  Факт начало: {r[5].strftime('%d.%m %H:%M')}\n"
        if r[6]:
            text += f"  Факт конец: {r[6].strftime('%d.%m %H:%M')}\n"
        text += f"  Статус: {r[7]}\n\n"
    await message.answer(text[:4000])  # телеграм лимит