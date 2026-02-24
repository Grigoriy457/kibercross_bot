from __future__ import annotations

import platform
import asyncio
import logging
from aiogram import types

from dispatcher import bot, dp
from dispatcher import DbSessionMiddleware, PrivacyPolicyCheckerMiddleware, IgnoreTelegramErrorsMiddleware
import bot_logger

import config
import handlers


logger = bot_logger.get_logger("main", level=logging.INFO)


async def main():
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(PrivacyPolicyCheckerMiddleware(bot=bot))
    dp.include_routers(handlers.router)

    await bot.set_my_commands([
        types.bot_command.BotCommand(command=i[0], description=i[1])
        for i in config.COMMANDS
    ])

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
