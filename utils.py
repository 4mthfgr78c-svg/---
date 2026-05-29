# utils.py
import asyncio
from datetime import datetime
from aiogram import Bot
from database import get_shifts_for_reminder, get_shifts_for_tomorrow

async def reminder_job(bot: Bot):
    """Запускать каждый час. Отправляет уведомления за час и за сутки."""
    # За час до смены
    one_hour_shifts = get_shifts_for_reminder(1)
    for shift_id, worker_id, obj_name, start_time in one_hour_shifts:
        try:
            await bot.send_message(worker_id, f"⏰ Напоминание: через час у вас смена на объекте «{obj_name}» в {start_time.strftime('%H:%M')}.")
        except:
            pass
    # Смены на завтра (проверяем, что сейчас 20:00)
    now = datetime.now()
    if now.hour == 20:
        tomorrow_shifts = get_shifts_for_tomorrow()
        for shift_id, worker_id, obj_name, start_time in tomorrow_shifts:
            try:
                await bot.send_message(worker_id, f"📆 Напоминание: завтра у вас смена на объекте «{obj_name}» в {start_time.strftime('%H:%M')}.")
            except:
                pass