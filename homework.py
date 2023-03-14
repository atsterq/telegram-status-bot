import logging
import os
import sys
import time
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


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug("Cообщение в Telegram чат отправлено.")
    except Exception as error:
        logger.error(f"Ошибка при отправке сообщения в Telegram чат: {error}")


# Убедитесь, что в функции `get_api_answer` обрабатывается ситуация,
# когда API домашки возвращает код, отличный от 200.
def get_api_answer(timestamp):
    """Делает запрос к эндпоинту API-сервиса."""
    try:
        response = requests.get(
            url=ENDPOINT, headers=HEADERS, params={"from_date": timestamp}
        )
        if response.status_code != 200:
            logger.error("API домашки возвращает код, отличный от 200.")
            raise 
        return response.json()
    except Exception as error:
        logger.error(f"Сбой в работе программы: {error}")


# Убедитесь, что функция `check_response` выбрасывает исключение,
# если в ответе API домашки нет ключа `homeworks`.
# Убедитесь, что функция `check_response` выбрасывает исключение `TypeError`,
# если в ответе API домашки под ключом `homeworks` данные приходят не в виде списка.
def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    return response.get("homework")


# Убедитесь, что функция `parse_status` обрабатывает случай, когда API домашки
# возвращает недокументированный статус домашней работы либо домашку без статуса.
# Убедитесь, что функция `parse_status` выбрасывает исключение,
# когда в ответе API домашки нет ключа `homework_name`.
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
    timestamp = int(time.time())  # - RETRY_PERIOD
    last_error = ""
    logger.debug("Проверка доступности переменных окружения.")
    if not check_tokens():
        logger.critical("Отсутствуют переменные окружения!")
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
                logger.debug("Нет нового статуса")
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
