from __future__ import annotations

import asyncio
from typing import Callable, Awaitable, Dict, Any, Union
import functools
import datetime

import aiogram
import aiogram.exceptions
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.base import BaseStorage, StorageKey, StateType
from aiogram.fsm.state import State
from aiogram import BaseMiddleware
import sqlalchemy.exc

import config
import database


import bot_logger
logger = bot_logger.get_logger("aiogram")


if not config.BOT_TOKEN:
    exit("No token provided")


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()

    async def __call__(
            self,
            handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: types.TelegramObject,
            data: Dict[str, Any],
    ) -> Any:
        async with database.Database() as db:
            async with db.session() as db_session:
                data["db"] = db
                data["db_session"] = db_session
                try:
                    ret = await handler(event, data)
                    await db_session.commit()
                    return ret

                except sqlalchemy.exc.IntegrityError:
                    logger.exception("Data base error")
                    await db_session.rollback()


class PrivacyPolicyCheckerMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def __call__(self,
                       handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: types.TelegramObject,
                       data: Dict[str, Any]) -> Any:
        if (event.callback_query is not None) and (event.callback_query.data == "start__confirm_privacy"):
            return await handler(event, data)

        user_id = (event.message or event.callback_query).from_user.id
        if user_id == bot.id:
            return await handler(event, data)

        message = (event.message or event.callback_query.message)
        if message.from_user.chat.type != "private":
            return None

        db_session: database.AsyncSession = data["db_session"]
        tg_user = await db_session.scalar(
            database.select(database.models.tg.TgUser)
            .where(database.models.tg.TgUser.id == user_id)
        )
        if (tg_user is None) or (not tg_user.is_policy_confirmed):
            await message.answer(
                '<b>👋 Добро пожаловать на регистрацию «Фиджитал-турнира: Киберкросс»!</b>\n\n'
                '<i>Перед началом регистрации просим подтвердить, что ты даёшь согласие на обработку персональных данных в соответствии с Федеральным законом «О персональных данных» от 27.07.2006 N 152-ФЗ.</i>',
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="✅ Подтверждаю", callback_data="start__confirm_privacy")
                ]])
            )
            return None
        return await handler(event, data)


class IgnoreTelegramErrorsMiddleware(BaseMiddleware):
    def __init__(self, bot: Bot):
        self.bot = bot

    async def __call__(self,
                       handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
                       event: types.TelegramObject,
                       data: Dict[str, Any]) -> Any:
        try:
            return await handler(event, data)

        except aiogram.exceptions.TelegramForbiddenError:
            if data.get("db_session") is None:
                return

            user_id = (event.message or event.callback_query).from_user.id
            db_user = await data["db_session"].scalar(
                database.select(database.models.tg.TgUser)
                .where(database.models.tg.TgUser.id == user_id)
            )
            db_user.is_deactivated = True
            await data["db_session"].merge(db_user)

            chat_id = (event.message or event).chat.id
            db_user_state = await data["db_session"].scalar(
                database.select(database.models.tg.FsmData)
                .where(database.models.tg.FsmData.chat_id == chat_id)
                .where(database.models.tg.FsmData.user_id == user_id)
            )
            if db_user_state is not None:
                await data["db_session"].delete(db_user_state)
            await data["db_session"].commit()

        except aiogram.exceptions.TelegramBadRequest as exception:
            patterns = (
                "Bad Request: message is not modified",
                "Bad Request: message can't be edited",
                "Bad Request: message can't be deleted for everyone"
            )
            if any(pattern in str(exception) for pattern in patterns):
                user_id = (event.message or event.callback_query).from_user.id
                logger.warning(f"Error when calling bot handler (id={user_id})",
                               exc_info=True, extra=bot_logger.get_extra_by_locals(locals()))
                return

            logger.exception("Error when calling bot handler", exc_info=True, extra=bot_logger.get_extra_by_locals(locals()))


def with_db_session(func):
    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        async with self.database as db:
            async with db.session() as db_session:
                return await func(self, db_session, *args, **kwargs)
    return wrapper


class MysqlStorage(BaseStorage):
    def __init__(self) -> None:
        self.database = database.Database()

    async def close(self) -> None:
        pass

    @with_db_session
    async def set_state(self, db_session: database.AsyncSession, key: StorageKey, state: StateType = None) -> None:
        db_state = await db_session.scalar(
            database.select(database.models.tg.FsmData)
            .where(database.models.tg.FsmData.chat_id == key.chat_id)
            .where(database.models.tg.FsmData.user_id == key.user_id)
        )
        if state is None:
            if db_state is not None:
                await db_session.delete(db_state)
                await db_session.commit()
            return

        if db_state is None:
            db_state = database.models.tg.FsmData(chat_id=key.chat_id, user_id=key.user_id)
        db_state.state = state.state if isinstance(state, State) else str(state)
        await db_session.merge(db_state)
        await db_session.commit()

    @with_db_session
    async def get_state(self, db_session: database.AsyncSession, key: StorageKey) -> None:
        db_state = await db_session.scalar(
            database.select(database.models.tg.FsmData)
            .where(database.models.tg.FsmData.chat_id == key.chat_id)
            .where(database.models.tg.FsmData.user_id == key.user_id)
        )
        return db_state.state if db_state is not None else None

    @with_db_session
    async def set_data(self, db_session: database.AsyncSession, key: StorageKey, data: Dict[str, Any]) -> None:
        db_state = await db_session.scalar(
            database.select(database.models.tg.FsmData)
            .where(database.models.tg.FsmData.chat_id == key.chat_id)
            .where(database.models.tg.FsmData.user_id == key.user_id)
        )
        if not data:
            if db_state is not None:
                await db_session.delete(db_state)
                await db_session.commit()
            return

        if db_state is None:
            db_state = database.models.tg.FsmData(chat_id=key.chat_id, user_id=key.user_id)

        if db_state.data is None:
            new_data = data
        else:
            new_data = db_state.data.copy()
            new_data.update(data)
        db_state.data = new_data
        await db_session.merge(db_state)
        await db_session.commit()

    @with_db_session
    async def get_data(self, db_session: database.AsyncSession, key: StorageKey) -> Dict[str, Any]:
        db_state = await db_session.scalar(
            database.select(database.models.tg.FsmData)
            .where(database.models.tg.FsmData.chat_id == key.chat_id)
            .where(database.models.tg.FsmData.user_id == key.user_id)
        )
        return db_state.data if db_state is not None else {}

    async def update_data(self, key: StorageKey, data: Dict[str, Any]) -> Dict[str, Any]:
        await self.set_data(key=key, data=data)
        return await self.get_data(key=key)


bot = Bot(config.BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML', link_preview_is_disabled=True))
dp = Dispatcher(storage=MysqlStorage())
