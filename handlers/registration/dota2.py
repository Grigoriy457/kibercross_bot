import re
from typing import Union

from aiogram import types, Router, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import constants.keyboard
from dispatcher import logger
import database

from handlers.registration.final import final_message

router = Router()


class Dota2registrationForm(StatesGroup):
    steam_id = State()
    own_devices = State()
    empty = State()


@router.callback_query(F.data == "register__discipline_dota2")
async def register__discipline_dota2(callback: types.CallbackQuery, state: FSMContext, db_session: database.AsyncSession):
    new_message = await callback.message.answer(
        "Пришли ссылку на свой профиль в Steam (например, https://steamcommunity.com/id/username или https://steamcommunity.com/profiles/12345678901234567)"
    )
    await callback.message.delete()
    await state.update_data(new_message_id=new_message.message_id)
    await state.set_state(Dota2registrationForm.steam_id)

@router.message(Dota2registrationForm.steam_id)
@router.callback_query(F.data == "register__discipline_dota2__back_to_steam_id")
async def steam_id__handler(message: Union[types.Message, types.CallbackQuery], bot: Bot, state: FSMContext):
    logger.info(f"[HANDLER] Steam id (id={message.from_user.id})")
    await state.set_state(Dota2registrationForm.steam_id)

    callback = None
    from_user = message.from_user
    if isinstance(message, types.CallbackQuery):
        callback = message
        steam_id = (await state.get_data()).get("steam_id")

    else:
        await message.delete()
        steam_id = message.text
        if (ret := re.match(r"^https?://steamcommunity\.com/(id|profiles)/([a-zA-Z0-9_]+)/?$", steam_id)) is None:
            await bot.edit_message_text(
                "<b>❌ Ошибка</b>\n\n"
                "Пришли ссылку на свой профиль в Steam (например, https://steamcommunity.com/id/username или https://steamcommunity.com/profiles/12345678901234567)",
                chat_id=from_user.id,
                message_id=(await state.get_data()).get("new_message_id")
            )
            await state.update_data(full_name=None)
            return

        if (await state.get_data()).get("steam_id") == steam_id:
            return
        await state.update_data(steam_id=steam_id, steam_id__fixed=ret.group(2))

    old_message_id = (await state.get_data()).get("new_message_id")
    if callback is not None:
        old_message_id = callback.message.message_id

    await bot.edit_message_text(
        "<b>Пришли ссылку на свой профиль в Steam (например, https://steamcommunity.com/id/username или https://steamcommunity.com/profiles/12345678901234567):</b>\n\n"
        f"<i>&gt; {steam_id}</i>",
        chat_id=from_user.id,
        message_id=old_message_id,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="▶️ Далее", callback_data="register__discipline_dota2__after_steam_id")
        ]])
    )


@router.callback_query(F.data == "register__discipline_dota2__after_steam_id")
async def after_steam_id_nickname__handler(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[HANDLER] After steam id (id={callback.from_user.id})")

    new_message = await callback.message.answer(
        'Ты принесёшь свои девайсы на турнир?',
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="✅ Да", callback_data="register__discipline_dota2__own_devices_yes"),
            types.InlineKeyboardButton(text="❌ Нет", callback_data="register__discipline_dota2__own_devices_no")
        ]])
    )
    await callback.message.delete()

    await state.update_data(new_message_id=new_message.message_id, birthdate=None)
    await state.set_state(Dota2registrationForm.own_devices)


@router.callback_query(F.data == "register__discipline_dota2__own_devices_yes")
@router.callback_query(F.data == "register__discipline_dota2__own_devices_no")
async def own_devices__handler(callback: types.CallbackQuery, state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] Own devices (id={callback.from_user.id})")

    is_bring_own_devices = (callback.data == "register__discipline_dota2__own_devices_yes")
    await state.update_data(is_bring_own_devices=is_bring_own_devices)

    await callback.message.delete()

    state_data = await state.get_data()
    await state.clear()
    db_registration = await db_session.scalar(
        database.select(database.models.registration.Registration)
        .where(database.models.registration.Registration.tg_user_id == callback.from_user.id)
    )
    if db_registration is None:
        await callback.message.edit_text(
            "❌ Ошибка\n\n"
            "Пожалуйста, начни регистрацию заново, нажав на кнопку 'регистрация'",
            reply_markup=constants.keyboard.main_keyboard__with_registration
        )
        return

    db_registration.dota2_steam_id = state_data.get("steam_id__fixed")
    db_registration.dota2_is_bring_own_devices = state_data.get("is_bring_own_devices")
    db_registration.discipline_dota2 = True
    await db_session.merge(db_registration)
    await db_session.commit()

    await callback.message.answer(
        "✅ Отлично!\n"
        "Теперь ты зарегистрирован на дисциплину Dota 2\n\n"
        "<i>Для регистрации на другие дисциплины нажми на кнопку 'моя регистрация' и добавь её</i>",
        message_effect_id="5046509860389126442",  # 🎉
        reply_markup=constants.keyboard.main_keyboard
    )
    await final_message(callback.message)
