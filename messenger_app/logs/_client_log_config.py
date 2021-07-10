import logging

"""
Создал 2 хендлера: для всех сообщений и для сообщений уровня warning и error
"""

logger = logging.getLogger("app.client")
logger.setLevel(logging.INFO)

fh = logging.FileHandler("logs/app.client.log", encoding="utf-8")
fh_warning = logging.FileHandler("logs/app.client_error_warning.log", encoding="utf-8")

formatter = logging.Formatter("%(asctime)s %(levelname)s %(module)s %(message)s")
fh.setFormatter(formatter)
fh_warning.setFormatter(formatter)
fh_warning.setLevel(logging.WARNING)

logger.addHandler(fh)
logger.addHandler(fh_warning)
