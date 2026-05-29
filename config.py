import os

BOT_TOKEN = "8812711404:AAGMMOmyyF7AO2q7E4e1D6IDZHL7t92Lnf4"

# Telegram ID менеджеров (можно несколько)
MANAGER_IDS = [123456789, 987654321]  # замените на реальные

# Путь к БД
DB_PATH = os.path.join(os.path.dirname(__file__), "cleaning.db")

# Часовой пояс для напоминаний (по Москве)
TIMEZONE = "Europe/Moscow"