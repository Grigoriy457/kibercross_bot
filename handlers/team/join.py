from aiogram import types, Router, F, Bot
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext

import constants.keyboard
from dispatcher import logger
import database


router = Router()


async def code_message_handler(message: types.Message, state: FSMContext, db_session: database.AsyncSession, bot: Bot, code: str):
    logger.info(f"[HANDLER] Team join by code (id={message.from_user.id})")
    await state.clear()

    db_team = await db_session.scalar(
        database.select(database.models.registration.Team)
        .where(database.models.registration.Team.code == code)
    )
    if db_team is None:
        await message.answer("❌ Неверный код команды")
        return

    db_registration = await db_session.scalar(
        database.select(database.models.registration.Registration)
        .where(database.models.registration.Registration.tg_user_id == message.from_user.id)
    )
    if db_registration is None:
        await message.answer(
            "❌ У тебя ещё нет регистрации\n\n"
            "Нажми на кнопку 'регистрация', чтобы начать её",
            reply_markup=constants.keyboard.main_keyboard__with_registration
        )
        return

    discipline_en = f"discipline_{db_team.discipline.value}"
    if db_registration.__getattribute__(discipline_en) is False:
        await message.answer(
            f"❌ Ты не зарегистрирован на дисциплину {dict(constants.DISCIPLINES)[discipline_en]}\n\n"
            f"Зарегистрируйся на {dict(constants.DISCIPLINES)[discipline_en]}, чтобы присоединиться к команде '{db_team.title}'",
            reply_markup=constants.keyboard.main_keyboard
        )
        return

    team_memberships = await db_registration.awaitable_attrs.team_memberships
    teams = [
        await team_membership.awaitable_attrs.team
        for team_membership in team_memberships
    ]
    if any(team.discipline == db_team.discipline for team in teams):
        await message.answer(
            "❌ Ты уже состоишь в команде этой дисциплины\n\n"
            "Покинь команду, чтобы присоединиться к этой",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="my_team")
            ]])
        )
        return

    if len(await db_team.awaitable_attrs.team_members) >= 5:
        await message.answer("❌ В команде уже 5 участников")
        return

    new_team_membership = database.models.registration.TeamMembers(
        team_id=db_team.id,
        registration_id=db_registration.id
    )
    db_session.add(new_team_membership)
    await db_session.commit()

    await message.answer(
        f"✅ Ты успешно присоединился к команде '{db_team.title}'!\n\n"
        "Теперь ты можешь увидеть её в разделе 'моя команда'",
        message_effect_id="5046509860389126442",  # 🎉
        reply_markup=constants.keyboard.main_keyboard
    )
    await bot.send_message(
        chat_id=await (await db_team.awaitable_attrs.owner_registration).awaitable_attrs.tg_user_id,
        text=f"👤 {db_registration.full_name} ({db_registration.nickname}) присоединился к твоей команде '{db_team.title}'!"
    )
