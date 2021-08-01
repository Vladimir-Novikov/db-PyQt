import logging
from logging.handlers import TimedRotatingFileHandler

logger = logging.getLogger("app.server")
logger.setLevel(logging.INFO)

fh = TimedRotatingFileHandler("logs/app.server.log", when="d", interval=1, backupCount=15, encoding="utf-8")


formatter = logging.Formatter("%(asctime)s %(levelname)s %(module)s function: %(funcName)s %(message)s")
fh.setFormatter(formatter)

logger.addHandler(fh)
