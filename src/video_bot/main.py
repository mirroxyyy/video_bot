import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from video_bot.config import get_config
from video_bot.database.database import create_tables, get_sessionmaker
from video_bot.handler import router
from video_bot.middleware import DIMiddleware


async def main() -> None:

    dp = Dispatcher()

    bot = Bot(
        token=get_config().BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    engine, sessionmaker = await get_sessionmaker()
    dp.update.middleware(DIMiddleware(sessionmaker))

    await create_tables(engine)

    dp.include_router(router)
    await dp.start_polling(bot)

    # shutdown
    await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
