from typing import Union
from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext

import constants
import constants.keyboard
from dispatcher import logger
import database

from handlers.registration.cs2 import register__discipline_cs2
from handlers.registration.dota2 import register__discipline_dota2


router = Router()


@router.message(F.text == constants.keyboard.keyboard__buttons["my_registration"])
@router.callback_query(F.data == "register__my_registration")
async def my_registration__handler(message: Union[types.Message, types.CallbackQuery], state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] My registration (id={message.from_user.id})")
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

    text = "🎫 Твоя регистрация:\n<blockquote>"
    text += f"<b>ФИО:</b> {db_registration.full_name}\n"
    text += f"<b>Дата рождения:</b> {db_registration.birthdate.strftime('%d.%m.%Y')}\n"
    if db_registration.from_bmstu:
        text += f"<b>Учебная группа:</b> {db_registration.edu_group}\n"
    else:
        text += f"<b>ВУЗ:</b> {db_registration.university}\n"
        text += f"<b>Серия и номер паспорта:</b> {db_registration.passport_data}\n"
    text += f"<b>Номер телефона:</b> {db_registration.phone_number}\n"
    text += f"<b>Никнейм:</b> {db_registration.nickname}\n"
    text += "</blockquote>\n\n"
    text += "🕹 Дисциплины:\n"
    text += f"{'✅' if db_registration.discipline_cs2 else '❌'} Counter-Strike 2\n"
    text += f"{'✅' if db_registration.discipline_dota2 else '❌'} Dota 2\n"
    text += f"{'✅' if db_registration.discipline_fifa else '❌'} EA FC\n\n"
    text += "<i>Чтобы изменить дисциплины, нажми на кнопку ниже</i>"

    await message.answer(
        text,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text=f"{'✅' if db_registration.__getattribute__(discipline_en) else '❌'} {discipline_name}",
                    callback_data=f"register__my_registration__{discipline_en}"
                )
                for discipline_en, discipline_name in constants.DISCIPLINES
            ],
            [types.InlineKeyboardButton(text="Отменить регистрацию", callback_data="cancel_registration__from_my_registration", style="danger")]
        ])
    )


@router.callback_query(F.data.startswith("register__my_registration__discipline_"))
async def register_discipline__handler(callback: types.CallbackQuery, state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] Register discipline from my registration (id={callback.from_user.id})")

    discipline_en = callback.data.split("__")[-1]

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

    current_value = db_registration.__getattribute__(discipline_en)
    if not current_value:
        conditions = (
            discipline_en == "discipline_cs2" and (db_registration.cs2_steam_id is not None),
            discipline_en == "discipline_dota2" and (db_registration.dota2_steam_id is not None),
            discipline_en == "discipline_fifa"
        )
        if any(conditions):
            db_registration.__setattr__(discipline_en, True)
            await db_session.merge(db_registration)
            await db_session.commit()

            await callback.message.edit_text(
                "✅ Дисциплина добавлена",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="◀️ Назад", callback_data="register__my_registration")
                ]])
            )
        else:
            if discipline_en == "discipline_cs2":
                await register__discipline_cs2(callback, state, db_session)
            elif discipline_en == "discipline_dota2":
                await register__discipline_dota2(callback, state, db_session)
            else:
                await callback.message.answer("❌ Ошибка\n\nНеизвестная дисциплина")
        return

    db_registration.__setattr__(discipline_en, False)
    await db_session.merge(db_registration)
    await db_session.commit()

    await callback.message.edit_text(
        "✅ Дисциплина удалена",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="register__my_registration")
        ]])
    )
