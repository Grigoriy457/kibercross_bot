import aiogram.exceptions
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext

import constants
import constants.keyboard
from dispatcher import logger, bot
import database


router = Router()


@router.callback_query(F.data == "my_team__exit")
async def my_team__exit__handler(callback: types.CallbackQuery, state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] My team exit (id={callback.from_user.id})")
    await state.clear()

    from_user = callback.from_user

    db_registration = await db_session.scalar(
        database.select(database.models.registration.Registration)
        .where(database.models.registration.Registration.tg_user_id == from_user.id)
    )
    if db_registration is None:
        await callback.message.edit_text(
            "❌ У тебя ещё нет регистрации\n\n"
            "Нажми на кнопку \"регистрация\", чтобы начать её",
            reply_markup=constants.keyboard.main_keyboard__with_registration
        )
        return

    team_memberships = await db_registration.awaitable_attrs.team_memberships
    if len(team_memberships) == 0:
        await callback.message.edit_text(
            "❌ У тебя нет команд\n\n"
            "Нажми на кнопку \"моя команда\", чтобы создать или вступить в команду",
            reply_markup=constants.keyboard.main_keyboard
        )
        return

    teams = [
        await team_membership.awaitable_attrs.team
        for team_membership in team_memberships
    ]

    buttons = [
        [types.InlineKeyboardButton(
            text=f"{team.title} ({team.discipline.value})",
            icon_custom_emoji_id="5879915802815107172", # 🗑
            callback_data=f"my_team__exit__{team.id}"
        )]
        for team in teams
    ]
    await callback.message.edit_text(
        "<tg-emoji emoji-id='6030848053177486888'>❓</tg-emoji> Из какой команды ты хочешь выйти?\n\n"
        "Если ты капитан, то вся команда будет удалена",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=buttons + [
            [types.InlineKeyboardButton(
                text="Назад",
                icon_custom_emoji_id="5960671702059848143",  # ◀️
                callback_data="my_team"
            )]
        ])
    )


@router.callback_query(F.data.startswith("my_team__exit__"))
async def my_team__exit__confirm_handler(callback: types.CallbackQuery, db_session: database.AsyncSession):
    team_id = int(callback.data.split("__")[-1])

    team_id = await db_session.get(database.models.registration.Team, team_id)
    if team_id is None:
        await callback.answer("❌ Команда не найдена", show_alert=True)
        return
    team_membership = await db_session.scalar(
        database.select(database.models.registration.TeamMembers)
        .where(database.models.registration.TeamMembers.team_id == team_id.id)
        .where(database.models.registration.TeamMembers.registration.has(
            database.models.registration.Registration.tg_user_id == callback.from_user.id
        ))
    )
    if team_membership is None:
        await callback.answer("❌ Ты не состоишь в этой команде", show_alert=True)
        return

    team = await team_membership.awaitable_attrs.team
    if team.owner_registration_id == team_membership.registration_id:
        for team_membership in await team.awaitable_attrs.team_members:
            if team_membership.registration_id == team.owner_registration_id:
                continue
            try:
                await bot.send_message(
                    (await team_membership.awaitable_attrs.registration).tg_user_id,
                    f"<tg-emoji emoji-id='5447644880824181073'>⚠️</tg-emoji> Капитан покинул команду "
                    f"\"{team.title}\" ({team.discipline.value}), команда удалена"
                )
            except aiogram.exceptions.TelegramForbiddenError:
                pass
        await db_session.delete(team)

    else:
        db_registration = await team_membership.awaitable_attrs.registration
        try:
            await bot.send_message(
                (await team.awaitable_attrs.owner_registration).tg_user_id,
                f"<tg-emoji emoji-id='5447644880824181073'>⚠️</tg-emoji> {db_registration.full_name} "
                f"({db_registration.nickname}) покинул твою команду \"{team.title}\" ({team.discipline.value})"
            )
        except aiogram.exceptions.TelegramForbiddenError:
            pass
        await db_session.delete(team_membership)
    await db_session.commit()

    await callback.message.delete()
    await callback.message.answer(
        "<tg-emoji emoji-id='5427009714745517609'>✅</tg-emoji> Ты успешно вышел из команды\n\n"
        "Нажми на кнопку \"моя команда\", чтобы создать или вступить в команду",
        reply_markup=constants.keyboard.main_keyboard
    )

