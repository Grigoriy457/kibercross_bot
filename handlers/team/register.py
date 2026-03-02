from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import random
import string

import constants
import constants.keyboard
from dispatcher import logger
import database


class RegistrationForm(StatesGroup):
    team_title = State()


router = Router()


@router.callback_query(F.data == "my_team__register")
async def my_team__register(callback: types.CallbackQuery, db_session: database.AsyncSession):
    db_registration = await db_session.scalar(
        database.select(database.models.registration.Registration)
        .where(database.models.registration.Registration.tg_user_id == callback.from_user.id)
    )
    if db_registration is None:
        await callback.message.edit_text(
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
    disciplines = [
        database.models.registration.DisciplineEnum.CS2,
        database.models.registration.DisciplineEnum.DOTA2,
        database.models.registration.DisciplineEnum.FIFA
    ]
    for team in teams:
        if team.discipline in disciplines:
            disciplines.remove(team.discipline)
    if len(disciplines) == 0:
        await callback.message.edit_text(
            "❌ У тебя уже есть команды во всех дисциплинах\n\n"
            "Покинь команду, чтобы создать новую",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5960671702059848143", callback_data="my_team")
            ]])
        )
        return

    await callback.message.edit_text(
        "Выбери дисциплину, в которой хочешь зарегистрировать команду",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Counter-Strike 2", callback_data="my_team__register__discipline_cs2"),
                types.InlineKeyboardButton(text="Dota 2", callback_data="my_team__register__discipline_dota2"),
                types.InlineKeyboardButton(text="EA FC", callback_data="my_team__register__discipline_fifa")
            ],
            [types.InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5960671702059848143", callback_data="my_team")]
        ])
    )


@router.callback_query(F.data.startswith("my_team__register__discipline_"))
async def my_team__register__discipline(callback: types.CallbackQuery, state: FSMContext, db_session: database.AsyncSession):
    discipline = callback.data.split("__")[-1].split("_")[-1].upper()

    db_registration = await db_session.scalar(
        database.select(database.models.registration.Registration)
        .where(database.models.registration.Registration.tg_user_id == callback.from_user.id)
    )
    team = await db_session.scalar(
        database.select(database.models.registration.TeamMembers)
        .join(database.models.registration.Team)
        .where(database.models.registration.TeamMembers.registration_id == db_registration.id)
        .where(database.models.registration.Team.discipline == database.models.registration.DisciplineEnum[discipline])
    )
    if team is not None:
        await callback.message.edit_text(
            "❌ У тебя уже есть команда в этой дисциплине\n\n"
            "Покинь команду, чтобы создать новую",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5960671702059848143", callback_data="my_team")
            ]])
        )
        return

    await state.set_state(RegistrationForm.team_title)
    await state.update_data(discipline=discipline)
    await callback.message.edit_text(
        "Напиши название своей команды",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5960671702059848143", callback_data="my_team")
        ]])
    )


@router.message(RegistrationForm.team_title)
async def my_team__register__team_title(message: types.Message, state: FSMContext, db_session: database.AsyncSession):
    state_data = await state.get_data()
    discipline = state_data["discipline"]

    team_title = message.text
    if len(team_title) > 15:
        await message.answer(
            "❌ Название команды слишком длинное (до 15 символов)\n"
            "Напиши название своей команды",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5960671702059848143", callback_data="my_team")
            ]])
        )
        return

    db_registration = await db_session.scalar(
        database.select(database.models.registration.Registration)
        .where(database.models.registration.Registration.tg_user_id == message.from_user.id)
    )
    new_team = database.models.registration.Team(
        code=''.join(random.choices(string.ascii_letters, k=10)),
        title=team_title,
        discipline=database.models.registration.DisciplineEnum[discipline],
        owner_registration_id=db_registration.id
    )
    db_session.add(new_team)
    db_session.add(database.models.registration.TeamMembers(
        team=new_team,
        registration_id=db_registration.id,
        is_capitan=True
    ))
    await db_session.commit()

    await state.clear()
    await message.answer(
        f"<tg-emoji emoji-id='5427009714745517609'>✅</tg-emoji> Команда \"{team_title}\" успешно создана!\n\n"
        "Пригласи своих друзей в команду, чтобы участвовать в турнире",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="Назад", icon_custom_emoji_id="5960671702059848143", callback_data="my_team"),
            types.InlineKeyboardButton(
                text="Пригласить",
                icon_custom_emoji_id = "5832251986635920010",
                switch_inline_query=f"приглашаю тебя в команду \"{team_title}\" по ссылке: t.me/cyberkross_2026_bot?start=team_{new_team.code}"
            )
        ]])
    )
