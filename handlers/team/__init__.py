from typing import Union
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext

import constants
import constants.keyboard
from dispatcher import logger
import database

from handlers.team import register as team_register, join as team_join, exit as team_exit, share as team_share


router = Router()
router.include_router(team_register.router)
router.include_router(team_exit.router)
router.include_router(team_share.router)


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
            "Нажми на кнопку \"регистрация\", чтобы начать её",
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
            for team_membership in sorted((await team.awaitable_attrs.team_members), key=lambda t: t.created_at)
        ]
        text = "<blockquote>"
        for member_registration in team_members:
            text += f"— {member_registration.full_name} ({member_registration.nickname}){' - капитан' if member_registration.id == team.owner_registration_id else ''}\n"
        text += "</blockquote>\n"
        return text

    text = "<tg-emoji emoji-id='5370867268051806190'>🫂</tg-emoji> Твои команды:\n\n"
    text += "<b>Counter-Strike 2</b>"
    if database.models.registration.DisciplineEnum.CS2 not in teams_disciplines:
        text += " — <tg-emoji emoji-id='5980953710157632545'>❌</tg-emoji>\n"
    else:
        text += f" — {next(team.title for team in teams if team.discipline == database.models.registration.DisciplineEnum.CS2)}:\n"
        text += await format_team_text(database.models.registration.DisciplineEnum.CS2)
    text += "<b>Dota 2</b>"
    if database.models.registration.DisciplineEnum.DOTA2 not in teams_disciplines:
        text += " — <tg-emoji emoji-id='5980953710157632545'>❌</tg-emoji>\n"
    else:
        text += f" — {next(team.title for team in teams if team.discipline == database.models.registration.DisciplineEnum.DOTA2)}:\n"
        text += await format_team_text(database.models.registration.DisciplineEnum.DOTA2)
    text += "<b>EA FC</b>"
    if database.models.registration.DisciplineEnum.FIFA not in teams_disciplines:
        text += " — <tg-emoji emoji-id='5980953710157632545'>❌</tg-emoji>\n"
    else:
        text += f" — {next(team.title for team in teams if team.discipline == database.models.registration.DisciplineEnum.FIFA)}:\n"
        text += await format_team_text(database.models.registration.DisciplineEnum.FIFA)

    buttons = []
    if len(teams) > 0:
        buttons.append([
            types.InlineKeyboardButton(text="Пригласить", icon_custom_emoji_id="5832251986635920010", callback_data="my_team__share")
        ])
    await message.answer(
        text,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons + [
            [
                types.InlineKeyboardButton(text="Создать команду", icon_custom_emoji_id="5415965335192883624", callback_data="my_team__register"),
                types.InlineKeyboardButton(text="Покинуть команду", icon_custom_emoji_id="5978859389614821335", callback_data="my_team__exit")
            ]
        ])
    )
