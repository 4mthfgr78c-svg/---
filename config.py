import os

BOT_TOKEN = "ВАШ_ТОКЕН"

# Telegram ID менеджеров (можно несколько)
MANAGER_IDS = [123456789, 987654321]  # замените на реальные

# Путь к БД
DB_PATH = os.path.join(os.path.dirname(__file__), "cleaning.db")

# Часовой пояс для напоминаний (по Москве)
TIMEZONE = "Europe/Moscow"