import logging
from functools import wraps
import inspect

logger = logging.getLogger("app.client")
logger.setLevel(logging.INFO)
fh = logging.FileHandler("logs/app.client.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)


def log(level="info"):
    """декоратор принимает параметры - уровень, по умолчанию = info"""

    def decorator(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            name = func.__name__
            # если ф-цию вызвала другая ф-ция - передаем ее имя в переменную main_function
            main_function = inspect.stack()[1][3]
            result = func(*args, **kwargs)
            if main_function != "<module>":
                if level == "info":
                    logger.info(
                        f"Функция {name} вызвана из функции {main_function} с аргументами {args},{kwargs}, результат {result}"
                    )
                if level == "error":
                    logger.error(
                        f"Функция {name} вызвана из функции {main_function} с аргументами {args},{kwargs}, получена ошибка {result}"
                    )
            elif level == "info":
                logger.info(f"Функция {name} вызвана с аргументами {args},{kwargs}, результат {result}")
            elif level == "error" and result is None:
                logger.info(f"Функция {name} вызвана с аргументами {args},{kwargs}")
            else:
                level == "error"
                logger.error(f"Функция {name} вызвана с аргументами {args},{kwargs}, получена ошибка {result}")
            return result

        return wrapped

    return decorator
