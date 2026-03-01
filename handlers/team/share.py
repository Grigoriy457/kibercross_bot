import aiogram.exceptions
from aiogram import types, Router, F, Bot
from aiogram.fsm.context import FSMContext

import constants
import constants.keyboard
from dispatcher import logger
import database


router = Router()


@router.callback_query(F.data == "my_team__share")
async def my_team__share(callback: types.CallbackQuery, state: FSMContext, db_session: database.AsyncSession, bot: Bot):
    logger.info(f"[HANDLER] My team share (id={callback.from_user.id})")
    await state.clear()

    from_user = callback.from_user

    db_registration = await db_session.scalar(
        database.select(database.models.registration.Registration)
        .where(database.models.registration.Registration.tg_user_id == from_user.id)
    )
    if db_registration is None:
        await callback.message.edit_text(
            "❌ У тебя ещё нет регистрации\n\n"
            "Нажми на кнопку 'регистрация', чтобы начать её",
            reply_markup=constants.keyboard.main_keyboard__with_registration
        )
        return

    team_memberships = await db_registration.awaitable_attrs.team_memberships
    if len(team_memberships) == 0:
        await callback.message.edit_text(
            "❌ У тебя нет команд\n\n"
            "Нажми на кнопку 'моя команда', чтобы создать команду или вступи по ссылке",
            reply_markup=constants.keyboard.main_keyboard
        )
        return

    teams = [
        await team_membership.awaitable_attrs.team
        for team_membership in team_memberships
    ]

    bot_username = (await bot.me()).username
    buttons = [
        [types.InlineKeyboardButton(
            text=f"{team.title} ({team.discipline.value})",
            icon_custom_emoji_id="5832251986635920010", # arrow_right
            switch_inline_query=f"приглашаю тебя в команду \"{team.title}\" по ссылке: t.me/{bot_username}?start=team_{team.code}"
        )]
        for team in teams
    ]
    await callback.message.edit_text(
        "<tg-emoji emoji-id='5877465816030515018'>🔗</tg-emoji> Нажми на кнопку с командой и отправь приглашение своим друзьям",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons + [
            [types.InlineKeyboardButton(
                text="Назад",
                icon_custom_emoji_id="5960671702059848143",
                callback_data="my_team"
            )]
        ])
    )
