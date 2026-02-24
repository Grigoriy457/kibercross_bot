from typing import Union
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext

import constants
import constants.keyboard
from dispatcher import logger
import database

from handlers.team import register as team_register, join as team_join


router = Router()
router.include_router(team_register.router)


@router.message(F.text == constants.keyboard.keyboard__buttons["my_team"])
@router.callback_query(F.data == "my_team")
async def my_team__handler(message: Union[types.Message, types.CallbackQuery], state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] My team (id={message.from_user.id})")
    await state.clear()

    from_user = message.from_user
    if isinstance(message, types.CallbackQuery):
        message = message.message
        await message.delete()

    db_registration = await db_session.scalar(
        database.select(database.models.registration.Registration)
        .where(database.models.registration.Registration.tg_user_id == from_user.id)
    )
    if db_registration is None:
        await message.answer(
            "❌ У тебя ещё нет регистрации\n\n"
            "Нажми на кнопку 'регистрация', чтобы начать её",
            reply_markup=constants.keyboard.main_keyboard__with_registration
        )
        return

    team_memberships = await db_registration.awaitable_attrs.team_memberships
    teams = [
        await team_membership.awaitable_attrs.team
        for team_membership in team_memberships
    ]
    teams_disciplines = [team.discipline for team in teams]

    async def format_team_text(discipline_enum: database.models.registration.DisciplineEnum) -> str:
        team = next(team for team in teams if team.discipline == discipline_enum)
        team_members = [
            await team_membership.awaitable_attrs.registration
            for team_membership in (await team.awaitable_attrs.team_members)
        ]
        text = "<blockquote>"
        for member_registration in team_members:
            text += f"— {member_registration.full_name} ({member_registration.nickname}){' - капитан' if member_registration.id == team.owner_registration_id else ''}\n"
        text += "</blockquote>\n"
        return text

    text = "👥 Твои команды:\n\n"
    text += "Counter-Strike 2"
    if database.models.registration.DisciplineEnum.CS2 not in teams_disciplines:
        text += " — ❌\n"
    else:
        text += f" — ✅ {next(team.title for team in teams if team.discipline == database.models.registration.DisciplineEnum.CS2)}\n"
        text += await format_team_text(database.models.registration.DisciplineEnum.CS2)
    text += "Dota 2"
    if database.models.registration.DisciplineEnum.DOTA2 not in teams_disciplines:
        text += " — ❌\n"
    else:
        text += f" — ✅ {next(team.title for team in teams if team.discipline == database.models.registration.DisciplineEnum.DOTA2)}\n"
        text += await format_team_text(database.models.registration.DisciplineEnum.DOTA2)
    text += "EA FC"
    if database.models.registration.DisciplineEnum.FIFA not in teams_disciplines:
        text += " — ❌\n"
    else:
        text += f" — ✅ {next(team.title for team in teams if team.discipline == database.models.registration.DisciplineEnum.FIFA)}\n"
        text += await format_team_text(database.models.registration.DisciplineEnum.FIFA)

    await message.answer(
        text,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="➕ Пригласить", callback_data="main_menu")],
            [
                types.InlineKeyboardButton(text="⚔️ Создать команду", callback_data="my_team__register"),
                types.InlineKeyboardButton(text="❌ Покинуть команду", callback_data="my_team__exit")
            ]
        ])
    )
