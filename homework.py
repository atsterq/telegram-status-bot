import json
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv("PRACTICUM_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}
# PAYLOAD = {"from_date": 1549962000}


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}

# updater = Updater(TELEGRAM_TOKEN)
# dispatcher = updater.dispatcher

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# Указываем обработчик логов
handler = RotatingFileHandler(
    "my_logger.log", maxBytes=50000000, backupCount=5
)
logger.addHandler(handler)
# Создаем форматер
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Применяем его к хэндлеру
handler.setFormatter(formatter)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        message = f"Сбой в работе программы: {error}"
        logger.error(message)


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    try:
        response = requests.get(
            url=ENDPOINT, headers=HEADERS, params={"from_date": timestamp}
        )
        return response.json()
    except Exception as error:
        message = f"Сбой в работе программы: {error}"
        logger.error(message)


def check_response(response) -> bool:
    """Проверяет ответ API на соответствие документации."""
    return response.get("homework")


def parse_status(homework) -> str:
    """Извлекает из информации о конкретной домашней работе её статус."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    # Сделать запрос к API.
    # Проверить ответ.
    # Если есть обновления — получить статус работы из обновления
    # и отправить сообщение в Telegram.
    # Подождать некоторое время и вернуться в пункт 1.
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time()) - RETRY_PERIOD
    last_error = ""
    logger.debug("Проверка наличия токенов.")
    if not check_tokens():
        logger.critical("Отсутствуют токены!")
        sys.exit()
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            timestamp = response.get("current_date")
            if homework:
                current_homework = homework[0]
                lesson_name = current_homework["lesson_name"]
                hw_status = parse_status(current_homework)
                send_message(bot, f"{lesson_name} - {hw_status}")
            else:
                send_message(bot, "Нет нового статуса")
                logger.info("Нет нового статуса")
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(error)
            if message != last_error:
                send_message(bot, HOMEWORK_VERDICTS)
        finally:
            time.sleep(RETRY_PERIOD)
        # try:
        #     response = get_api_answer(timestamp)
        #     homework = check_response(response)
        #     message = parse_status(homework)
        # except Exception as error:
        #     message = f"Сбой в работе программы: {error}"
        #     logger.error(message)
        # finally:
        #     if sent_message == message:
        #         logger.debug(
        #             "Отправка отменена:"
        #             f"текст сообщения не изменился: {message}"
        #         )
        #         time.sleep(RETRY_PERIOD)
        #         continue
        #     try:
        #         send_message(bot, message)
        #         logger.debug(f"Успешная отправка сообщения: {message}")
        #     except Exception as error:
        #         logger.error(error)
        #     finally:
        #         sent_message = message
        #         time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
