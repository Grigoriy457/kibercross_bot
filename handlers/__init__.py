from aiogram import types, Router, F

from constants.keyboard import main_keyboard, main_keyboard__with_registration, admin_keyboard
from handlers import forms
from handlers import base_commands, registration, team
import database
import config


router = Router()
router.include_routers(
    base_commands.router,
    registration.router,
    team.router,
)


last_router = Router()
@last_router.message(F.chat.id != config.ADMIN_CHAT_ID)
async def unknown_command(message: types.Message, db_session: database.AsyncSession):
    if message.pinned_message is not None:
        # await message.delete()
        return

    user = await db_session.merge(
        database.models.tg.TgUser(id=message.from_user.id, username=message.from_user.username)
    )
    await db_session.commit()

    db_admin = await db_session.scalar(
        database.select(database.models.tg.Admin)
        .where(database.models.tg.Admin.tg_user_id == message.from_user.id)
    )
    if db_admin is not None:
        reply_markup = admin_keyboard
    elif (await user.awaitable_attrs.registration) is None:
        reply_markup = main_keyboard__with_registration
    else:
        reply_markup = main_keyboard
    await message.answer("Я тебя не понял 😢", reply_markup=reply_markup)


router.include_router(last_router)
