import logging

from video_bot.config import get_config


def setup_logger():
    config = get_config()

    logger = logging.getLogger()
    logger.setLevel(config.LOG_LEVEL.value)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(config.LOG_LEVEL.value)
    file_handler = logging.FileHandler("app.log")
    file_handler.setLevel(config.LOG_LEVEL.value)

    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logging.getLogger("uvicorn").handlers = logger.handlers
    logging.getLogger("uvicorn.access").handlers = logger.handlers
    logging.getLogger("fastapi").handlers = logger.handlers
