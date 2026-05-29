import re
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import MANAGER_IDS
from database import *
from keyboards import *
from states import *

router = Router()

# ---------- СТАРТ ----------
@router.message(Command("start"))
async def cmd_start(message: Message):
    tg_id = message.from_user.id
    register_user(tg_id, message.from_user.username, message.from_user.full_name)
    if is_manager(tg_id):
        await message.answer("👋 Здравствуйте, менеджер! Используйте кнопки ниже.", reply_markup=main_manager_keyboard())
    else:
        await message.answer("👋 Добро пожаловать, уборщица! Используйте кнопки для работы.", reply_markup=main_worker_keyboard())

# ---------- ГЛАВНОЕ МЕНЮ (возврат) ----------
@router.message(F.text == "🏠 Главное меню")
async def back_to_menu(message: Message):
    if is_manager(message.from_user.id):
        await message.answer("Главное меню менеджера:", reply_markup=main_manager_keyboard())
    else:
        await message.answer("Главное меню уборщицы:", reply_markup=main_worker_keyboard())

# ---------- МЕНЕДЖЕР: СОЗДАНИЕ ОБЪЕКТА ----------
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

# ---------- МЕНЕДЖЕР: УПРАВЛЕНИЕ ОБЪЕКТАМИ (РЕДАКТИРОВАТЬ/УДАЛИТЬ) ----------
@router.message(F.text == "✏️ Управление объектами")
async def manage_objects(message: Message):
    if not is_manager(message.from_user.id):
        return
    objects = get_objects()
    if not objects:
        await message.answer("Нет ни одного объекта. Сначала создайте объект.")
        return
    await message.answer("Выберите объект для редактирования или удаления:", reply_markup=manage_objects_inline(objects))

# Редактирование: начало
@router.callback_query(F.data.startswith("edit_obj_"))
async def edit_object_start(call: CallbackQuery, state: FSMContext):
    obj_id = int(call.data.split("_")[2])
    obj = get_object_by_id(obj_id)
    if not obj:
        await call.message.edit_text("Объект не найден.")
        await call.answer()
        return
    await state.update_data(edit_obj_id=obj_id)
    await call.message.edit_text(f"Редактируем объект «{obj[1]}».\nВведите новое название (или отправьте «пропустить», чтобы оставить как есть):")
    await state.set_state(EditObject.waiting_for_new_name)
    await call.answer()

@router.message(EditObject.waiting_for_new_name)
async def edit_object_new_name(message: Message, state: FSMContext):
    data = await state.get_data()
    obj_id = data["edit_obj_id"]
    obj = get_object_by_id(obj_id)
    if not obj:
        await message.answer("Ошибка: объект не найден.")
        await state.clear()
        return
    new_name = message.text if message.text.lower() != "пропустить" else obj[1]
    await state.update_data(new_name=new_name)
    await message.answer(f"Новое название: {new_name}\nТеперь введите новый адрес (или «пропустить»):")
    await state.set_state(EditObject.waiting_for_new_address)

@router.message(EditObject.waiting_for_new_address)
async def edit_object_new_address(message: Message, state: FSMContext):
    data = await state.get_data()
    obj_id = data["edit_obj_id"]
    obj = get_object_by_id(obj_id)
    if not obj:
        await message.answer("Ошибка: объект не найден.")
        await state.clear()
        return
    new_address = message.text if message.text.lower() != "пропустить" else obj[2]
    new_name = data["new_name"]
    update_object(obj_id, new_name, new_address)
    await message.answer(f"✅ Объект обновлён:\nНазвание: {new_name}\nАдрес: {new_address}", reply_markup=main_manager_keyboard())
    await state.clear()

# Удаление: запрос подтверждения
@router.callback_query(F.data.startswith("delete_obj_"))
async def delete_object_confirm(call: CallbackQuery):
    obj_id = int(call.data.split("_")[2])
    obj = get_object_by_id(obj_id)
    if not obj:
        await call.message.edit_text("Объект не найден.")
        await call.answer()
        return
    await call.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить объект «{obj[1]}»?\nВсе связанные смены также будут удалены.",
        reply_markup=confirm_delete_inline(obj_id, obj[1])
    )
    await call.answer()

@router.callback_query(F.data.startswith("confirm_del_"))
async def delete_object_final(call: CallbackQuery):
    obj_id = int(call.data.split("_")[2])
    delete_object(obj_id)
    await call.message.edit_text("✅ Объект удалён.")
    await call.answer()

@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(call: CallbackQuery):
    await call.message.edit_text("Удаление отменено.")
    await call.answer()

# ---------- МЕНЕДЖЕР: НАЗНАЧЕНИЕ СМЕНЫ ----------
@router.message(F.text == "📅 Назначить смену")
async def assign_shift_start(message: Message, state: FSMContext):
    if not is_manager(message.from_user.id):
        return
    workers = get_workers()
    if not workers:
        await message.answer("Нет зарегистрированных уборщиц. Попросите их запустить /start.")
        return
    await message.answer("Выберите уборщицу:", reply_markup=workers_inline(workers))
    await state.set_state(AssignShift.waiting_for_worker)

@router.callback_query(AssignShift.waiting_for_worker, F.data.startswith("worker_"))
async def assign_shift_worker(call: CallbackQuery, state: FSMContext):
    worker_id = int(call.data.split("_")[1])
    await state.update_data(worker_id=worker_id)
    objects = get_objects()
    if not objects:
        await call.message.edit_text("Сначала создайте хотя бы один объект командой «Создать объект».")
        await state.clear()
        return
    await call.message.edit_text("Выберите объект:", reply_markup=objects_inline(objects))
    await state.set_state(AssignShift.waiting_for_object)
    await call.answer()

@router.callback_query(AssignShift.waiting_for_object, F.data.startswith("obj_"))
async def assign_shift_object(call: CallbackQuery, state: FSMContext):
    object_id = int(call.data.split("_")[1])
    await state.update_data(object_id=object_id)
    await call.message.edit_text("Введите дату и время начала смены в формате: ГГГГ-ММ-ДД ЧЧ:ММ\nПример: 2025-06-15 10:00")
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

# ---------- МЕНЕДЖЕР: СОСТОЯНИЕ ОБЪЕКТОВ ----------
@router.message(F.text == "📍 Состояние объектов")
async def objects_status(message: Message):
    if not is_manager(message.from_user.id):
        return
    objects_data = get_objects_with_last_shift()
    if not objects_data:
        await message.answer("Нет ни одного объекта.")
        return
    text = "🏢 Состояние объектов:\n\n"
    for obj in objects_data:
        obj_id, name, address, last_worker, last_end, last_status = obj
        text += f"📍 {name}\n   Адрес: {address}\n"
        if last_worker:
            status_emoji = "✅" if last_status == "completed" else "🔄" if last_status == "in_progress" else "⏳"
            last_end_str = last_end.strftime("%d.%m %H:%M") if last_end else "не завершена"
            text += f"   Последняя смена: {last_worker}\n   {status_emoji} {last_status} {last_end_str}\n"
        else:
            text += "   Смен ещё не было.\n"
        text += "\n"
    await message.answer(text[:4000])

# ---------- МЕНЕДЖЕР: ЖУРНАЛ СМЕН ----------
@router.message(F.text == "📊 Журнал смен (все)")
async def all_shifts_log(message: Message):
    if not is_manager(message.from_user.id):
        return
    rows = get_all_shifts(50)
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
    await message.answer(text[:4000])

# ---------- МЕНЕДЖЕР: ЗАКАЗЫ МОЮЩИХ ----------
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

# ---------- УБОРЩИЦА: МОИ СМЕНЫ ----------
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

@router.callback_query(F.data.startswith("start_shift_"))
async def start_shift_callback(call: CallbackQuery):
    shift_id = int(call.data.split("_")[2])
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

# ---------- УБОРЩИЦА: ЗАВЕРШИТЬ СМЕНУ ----------
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

# ---------- УБОРЩИЦА: ЗАКАЗ МОЮЩИХ ----------
@router.message(F.text == "🧴 Заказать моющие")
async def order_supply(message: Message, state: FSMContext):
    await message.answer("Напишите, что нужно заказать (название, количество, примечания):")
    await state.set_state(SupplyOrder.waiting_for_text)

@router.message(SupplyOrder.waiting_for_text)
async def order_supply_text(message: Message, state: FSMContext):
    add_supply_order(message.from_user.id, message.text)
    await message.answer("✅ Заказ отправлен менеджеру.", reply_markup=main_worker_keyboard())
    await state.clear()
    for mgr in MANAGER_IDS:
        try:
            await message.bot.send_message(mgr, f"📦 Новый заказ моющих от {message.from_user.full_name}:\n{message.text}")
        except:
            pass