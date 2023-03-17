import logging
import os
import sys
import time
from http import HTTPStatus
from logging import StreamHandler

import requests
import telegram
from dotenv import load_dotenv
from requests import RequestException

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


def check_tokens() -> None:
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message: str) -> None:
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug("Cообщение в Telegram чат отправлено.")
    except Exception as error:
        logger.error(f"Ошибка при отправке сообщения в Telegram чат: {error}")


def get_api_answer(timestamp: int) -> dict:
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        response = requests.get(
            url=ENDPOINT, headers=HEADERS, params={"from_date": timestamp}
        )
        if response.status_code != HTTPStatus.OK:
            error = "API домашки возвращает код, отличный от 200."
            logger.error(error)
            raise Exception(error)
        return response.json()
    except RequestException as error:
        logger.error(f"Ошибка при запросе к эндпойнту: {error}")
        raise SystemError(error)


def check_response(response: dict) -> list:
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        error = (
            f"В ответе был получен объект типа {type(response)},"
            "ожидался объект типа dict"
        )
        logger.error(error)
        raise TypeError(error)
    if "homeworks" not in response:
        error = "в ответе API домашки нет ключа homeworks"
        logger.error(error)
        raise ValueError(error)
    homeworks = response.get("homeworks")
    if not isinstance(homeworks, list):
        error = (
            f"Под ключеи homeworks был получен объект типа {type(response)},"
            "ожидался объект типа list"
        )
        logger.error(error)
        raise TypeError(error)
    return response.get("homeworks")


def parse_status(homework: dict) -> str:
    """Извлекает из информации о конкретной домашней работе её статус."""
    homework_name = homework.get("homework_name")
    status = homework.get("status")
    try:
        if status not in HOMEWORK_VERDICTS.keys() or None:
            raise KeyError(
                "Отсутствующий или недокументированный статус домашки"
            )
        if "homework_name" not in homework or None:
            raise KeyError(f"В ответе API домашки нет ключа {homework_name}")
        verdict = HOMEWORK_VERDICTS[status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    except Exception as error:
        logger.error("Ошибка проверки ключей.")
        raise KeyError(error)


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
