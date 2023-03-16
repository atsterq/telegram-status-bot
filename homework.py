import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

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


HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message: str):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug("Cообщение в Telegram чат отправлено.")
    except Exception as error:
        logger.error(f"Ошибка при отправке сообщения в Telegram чат: {error}")


# Убедитесь, что в функции `get_api_answer` обрабатывается ситуация,
# когда API домашки возвращает код, отличный от 200. x2
def get_api_answer(timestamp: int) -> dict:
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        response = requests.get(
            url=ENDPOINT, headers=HEADERS, params={"from_date": timestamp}
        )
        if response.status_code != HTTPStatus.OK:
            error_message = "API домашки возвращает код, отличный от 200."
            logger.error(error_message)
            raise Exception(error_message)
        else:
            return response.json()
    except Exception as error:
        logger.error(f"Ошибка при запросе к эндпойнту: {error}")


# Убедитесь, что функция `check_response` выбрасывает исключение `TypeError`
# в случае, если в ответе API структура данных не соответствует ожиданиям:
# например, получен список вместо ожидаемого словаря.
def check_response(response: dict) -> list:
    """Проверяет ответ API на соответствие документации."""
    if "homeworks" not in response:
        error_message = "в ответе API домашки нет ключа homeworks"
        logger.error(error_message)
        raise ValueError(error_message)
    homeworks = response.get("homeworks")
    if not isinstance(homeworks, list):
        error_message = (
            f"Под ключеи homeworks был получен объект типа {type(response)},"
            "ожидался объект типа list"
        )
        logger.error(error_message)
        raise TypeError(error_message)
    if not isinstance(response, dict):
        error_message = (
            f"В ответе был получен объект типа {type(response)},"
            "ожидался объект типа dict"
        )
        logger.error(error_message)
        raise TypeError(error_message)
    return response.get("homeworks")


# Убедитесь, что функция `parse_status` обрабатывает случай, когда API домашки
# возвращает недокументированный статус домашней работы либо домашку без статуса.
# Убедитесь, что функция `parse_status` выбрасывает исключение,
# когда в ответе API домашки нет ключа `homework_name`.
def parse_status(homework: dict) -> str:
    """Извлекает из информации о конкретной домашней работе её статус."""
    homework_name = homework.get("homework_name")
    homework_status = homework.get("status")
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main() -> None:
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    sent_message = ""

    logger.debug("Проверка доступности переменных окружения.")
    if not check_tokens():
        logger.critical("Отсутствуют переменные окружения!")
        sys.exit()
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            # timestamp = response.get("current_date")
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
            else:
                status_message = "У текущей домашки нет нового статуса"
                send_message(bot, status_message)
                logger.debug(status_message)
        except Exception as error:
            message = f"Сбой в работе программы: {error}"
            logger.error(error)
            if message != sent_message:
                send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
