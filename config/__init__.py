from dotenv import dotenv_values
import platform
import logging
import datetime

config = dotenv_values("./config/.env")


IS_DEV = bool(int(config.get("IS_DEV", "0")))

BOT_TOKEN = config["BOT_TOKEN"]
SUPPORT_USERNAME = config["SUPPORT_USERNAME"]
ADMIN_CHAT_ID = int(config["ADMIN_CHAT_ID"])

DB_HOST = config["DB_HOST"]
DB_NAME = config["DB_NAME"]
DB_USER = config["DB_USER"]
DB_PASSWORD = config["DB_PASSWORD"]

COMMANDS = [
    ["start", "перезапуск бота"],
    ["info", "информация"],
    ["registration", "регистрация"],
    ["cancel_registration", "отмена регистрации"],
#    ["team", "моя команда"],
    ["help", "помощь"]
]
PARSE_MODE = "HTML"

LOGGING_LEVEL = logging.INFO
LOGGING_FORMAT = "%(levelname)s | %(asctime)s | %(name)s (%(filename)s).%(funcName)s(%(lineno)d) -> %(message)s"
LOGGING_DATEFORMAT = "%Y-%m-%d %H:%M:%S"
