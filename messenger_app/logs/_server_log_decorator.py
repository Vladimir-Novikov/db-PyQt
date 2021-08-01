import inspect
import logging
import pickle
from functools import wraps

logger = logging.getLogger("app.server")
logger.setLevel(logging.INFO)
fh = logging.FileHandler("logs/app.server.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)


def log(level="info", return_values=1):
    """
    декоратор принимает параметры - уровень, по умолчанию = info
    Кол-во вариантов возвращаемых значений (1 по умолчанию), 2 если ф-ция может вернуть более 1 варианта
    """

    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            name = func.__name__
            # если ф-цию вызвала другая ф-ция - передаем ее имя в переменную main_function
            main_function = inspect.stack()[1][3]
            result = func(*args, **kwargs)
            # если ф-ция возвращает более 1 варианта ответа - проверяем response
            if return_values > 1:
                if result["response"] > 200:
                    logger.error(f"Функция {name} вызвана с аргументами {args},{kwargs}, получена ошибка {result}")
                else:
                    logger.info(f"Функция {name} вызвана с аргументами {args},{kwargs}, результат {result}")

            if main_function != "<module>":
                if level == "info" and result is None:
                    logger.info(f"Функция {name} вызвана из функции {main_function} с аргументами {args},{kwargs}")
                if level == "info" and result is not None:
                    logger.info(
                        f"Функция {name} вызвана из функции {main_function} с аргументами {args},{kwargs}, результат {result}"
                    )
                if level == "error":
                    logger.error(
                        f"Функция {name} вызвана из функции {main_function} с аргументами {args},{kwargs}, получена ошибка {result}"
                    )
            if main_function == "<module>" and return_values == 1:
                if level == "info":
                    logger.info(f"Функция {name} вызвана с аргументами {args},{kwargs}, результат {result}")
                else:
                    logger.error(f"Функция {name} вызвана с аргументами {args},{kwargs}, получена ошибка {result}")
            return result

        return wrapped

    return decorator
