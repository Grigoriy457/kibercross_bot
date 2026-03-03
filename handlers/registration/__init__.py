import datetime
from dateutil.relativedelta import relativedelta
import re
from typing import Union
import sqlalchemy

import phonenumbers

import aiogram
import aiogram.exceptions
from aiogram import types, Router, Bot, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import config
import constants.keyboard
from dispatcher import logger
import database

from handlers.registration import cs2, dota2, fifa, my_registration


class RegistrationForm(StatesGroup):
    full_name = State()
    birthdate = State()
    education_group = State()
    university = State()
    passport_data = State()
    phone_number = State()
    nickname = State()
    empty = State()


router = Router()
router.include_routers(my_registration.router, cs2.router, dota2.router, fifa.router)


with open("./config/edu_groups.txt", "r", encoding="utf8") as f:
    edu_groups = f.read().split("\n")


@router.message(Command("registration"))
@router.message(F.text == constants.keyboard.keyboard__buttons["registration"])
async def registration(message: types.Message, state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] Register command (id={message.from_user.id})")
    await state.clear()

    tg_user = await db_session.merge(database.models.tg.TgUser(id=message.from_user.id, username=message.from_user.username))
    await db_session.commit()

    if (await tg_user.awaitable_attrs.registration) is not None:
        await message.answer(
            f"<b>❗️Ты уже зарегистрирован</b>\n\n"
            "<i>Для отмены регистрации нажми на кнопку ниже</i>",
            reply_markup=constants.keyboard.main_keyboard
        )
        return

    new_message = await message.answer('Для регистрации напиши свою фамилию, имя и отчество (при наличии)')
    await state.update_data(new_message_id=new_message.message_id)
    await state.set_state(RegistrationForm.full_name)


@router.message(Command("cancel_registration"))
@router.callback_query(F.data == "cancel_registration")
@router.callback_query(F.data == "cancel_registration__from_my_registration")
async def registration__cancel(message: Union[types.Message, types.CallbackQuery], state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] Registration cancel (id={message.from_user.id})")
    await state.clear()

    cancel_btn = "cancel_registration__cancel"

    tg_user = await db_session.merge(database.models.tg.TgUser(id=message.from_user.id, username=message.from_user.username))
    await db_session.commit()
    if isinstance(message, types.CallbackQuery):
        if message.data == "cancel_registration__from_my_registration":
            cancel_btn = "register__my_registration"
        message = message.message
        await message.delete()
    await state.update_data(message_id=message.message_id)

    if (await tg_user.awaitable_attrs.registration) is None:
        await message.answer("❗️ Ты еще не зарегистрирован", reply_markup=constants.keyboard.main_keyboard__with_registration)
        return
    await message.answer(
        "Ты уверен, что хочешь отменить регистрацию?\n"
        "Все созданные команды будут удалены",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="✅ Да", callback_data="cancel_registration__confirm"),
            types.InlineKeyboardButton(text="❌ Нет", callback_data=cancel_btn)
        ]])
    )


@router.callback_query(F.data == "cancel_registration__confirm")
async def registration__cancel__confirm(callback: types.CallbackQuery, state: FSMContext, bot: Bot, db_session: database.AsyncSession):
    await state.clear()
    await callback.message.delete()

    tg_user = await db_session.merge(database.models.tg.TgUser(id=callback.from_user.id, username=callback.from_user.username))
    await db_session.commit()
    if (db_registration := await tg_user.awaitable_attrs.registration) is None:
        await callback.message.answer("❗️ Ты еще не зарегистрирован", reply_markup=constants.keyboard.main_keyboard__with_registration)
        return

    if (team_memberships := await db_registration.awaitable_attrs.team_memberships) is not None:
        for team_membership in team_memberships:
            team = await team_membership.awaitable_attrs.team
            if team.owner_registration_id == db_registration.id:
                for member in (await team.awaitable_attrs.members):
                    if member.registration_id != db_registration.id:
                        try:
                            await bot.send_message(
                                chat_id=(await member.awaitable_attrs.registration).tg_user_id,
                                text=f"❗️ Команда \"{team.title}\" была удалена, так как её владелец отменил регистрацию"
                            )
                        except aiogram.exceptions.TelegramBadRequest:
                            pass
                await db_session.delete(team)
    await db_session.delete(db_registration)
    await db_session.commit()

    await callback.message.answer(
        "✅ Регистрация отменена",
        reply_markup=constants.keyboard.main_keyboard__with_registration
    )


@router.callback_query(F.data == "cancel_registration__cancel")
async def registration__cancel__cancel(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    try:
        message_id = (await state.get_data()).get("message_id")
        if message_id:
            await bot.delete_message(chat_id=callback.from_user.id, message_id=message_id)
    except aiogram.exceptions.TelegramBadRequest:
        pass
    await callback.message.delete()
    await state.clear()


@router.message(RegistrationForm.full_name)
@router.callback_query(F.data == "registration__back_to_full_name")
async def full_name__handler(message: Union[types.Message, types.CallbackQuery], bot: Bot, state: FSMContext):
    logger.info(f"[HANDLER] Full name (id={message.from_user.id})")
    await state.set_state(RegistrationForm.full_name)

    callback = None
    from_user = message.from_user
    if isinstance(message, types.CallbackQuery):
        callback = message
        full_name = (await state.get_data()).get("full_name")

    else:
        await message.delete()
        full_name = message.text
        if (len(full_name) < 5) or (len(full_name) > 100) or (len(full_name.split(" ")) < 2) or (len(re.findall(r"[а-яА-Я]|ё|\s|-", full_name)) < len(full_name)):
            await bot.edit_message_text(
                "<b>❌ Ошибка</b>\n\n"
                "Пожалуйста, напиши свою фамилию, имя и отчество (при наличии)",
                chat_id=from_user.id,
                message_id=(await state.get_data()).get("new_message_id")
            )
            await state.update_data(full_name=None)
            return

        if (await state.get_data()).get("full_name") == full_name:
            return
        await state.update_data(full_name=full_name)

    old_message_id = (await state.get_data()).get("new_message_id")
    if callback is not None:
        old_message_id = callback.message.message_id

    await bot.edit_message_text(
        "<b>Для регистрации напиши свою фамилию, имя и отчество (при наличии):</b>\n\n"
        f"<i>&gt; {full_name}</i>",
        chat_id=from_user.id,
        message_id=old_message_id,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="▶️ Далее", callback_data="register__after_full_name")
        ]])
    )


@router.callback_query(F.data == "register__after_full_name")
async def after_full_name__handler(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[HANDLER] After full name (id={callback.from_user.id})")

    new_message = await callback.message.answer(
        'Напиши свою дату рождения в формате <code>ДД.ММ.ГГГГ</code>',
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_full_name")
        ]])
    )
    await callback.message.delete()

    await state.update_data(new_message_id=new_message.message_id, birthdate=None)
    await state.set_state(RegistrationForm.birthdate)


@router.message(RegistrationForm.birthdate)
@router.callback_query(F.data == "registration__back_birthdate")
async def birthdate__handler(message: Union[types.Message, types.CallbackQuery], bot: Bot, state: FSMContext):
    logger.info(f"[HANDLER] Birthdate (id={message.from_user.id})")
    await state.set_state(RegistrationForm.birthdate)

    callback = None
    from_user = message.from_user
    if isinstance(message, types.CallbackQuery):
        callback = message
        birthdate = (await state.get_data()).get("birthdate")

    else:
        await message.delete()
        birthdate = message.text

        try:
            datetime.datetime.strptime(birthdate, "%d.%m.%Y")
        except ValueError:
            await bot.edit_message_text(
                "<b>❌ Ошибка</b>\n\n"
                "Пожалуйста, напиши свою дату рождения в формате <code>ДД.ММ.ГГГГ</code>",
                chat_id=from_user.id,
                message_id=(await state.get_data()).get("new_message_id"),
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_full_name")
                ]])
            )
            await state.update_data(birthdate=None)
            return

        if (await state.get_data()).get("birthdate") == birthdate:
            return
        await state.update_data(birthdate=birthdate)

    old_message_id = (await state.get_data()).get("new_message_id")
    if callback is not None:
        old_message_id = callback.message.message_id
    await bot.edit_message_text(
        "<b>Напиши свою дату рождения в формате <code>ДД.ММ.ГГГГ</code>:</b>\n\n"
        f"<i>&gt; {birthdate}</i>",
        chat_id=from_user.id,
        message_id=old_message_id,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_full_name"),
            types.InlineKeyboardButton(text="▶️ Далее", callback_data="register__after_birthdate")
        ]])
    )


@router.callback_query(F.data == "register__after_birthdate")
@router.callback_query(F.data == "registration__back_to_bmstu_edu")
async def after_birthdate__handler(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[HANDLER] After birthdate (id={callback.from_user.id})")

    new_message = await callback.message.answer(
        text='Ты обучаешься в МГТУ им. Н.Э. Баумана?',
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [
                types.InlineKeyboardButton(text="Да", callback_data="register__after_bmstu_education__yes"),
                types.InlineKeyboardButton(text="Нет", callback_data="register__after_bmstu_education__no")
            ],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_birthdate")]
        ])
    )
    await callback.message.delete()

    await state.update_data(new_message_id=new_message.message_id)
    await state.set_state(RegistrationForm.empty)


@router.callback_query(F.data == "register__after_bmstu_education__yes")
async def after_bmstu_edu__handler(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[HANDLER] After bmstu education (id={callback.from_user.id})")

    await state.update_data(bmstu_education=True, education_group=None)

    await callback.message.edit_text(
        "Напиши свою учебную группу",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_bmstu_edu")
        ]])
    )
    await state.set_state(RegistrationForm.education_group)


@router.message(RegistrationForm.education_group)
@router.callback_query(F.data == "registration__back_to_edu_group")
async def education_group__handler(message: Union[types.Message, types.CallbackQuery], bot: Bot, state: FSMContext):
    logger.info(f"[HANDLER] Education group (id={message.from_user.id})")
    await state.set_state(RegistrationForm.education_group)

    callback = None
    from_user = message.from_user
    if isinstance(message, types.CallbackQuery):
        callback = message
        education_group = (await state.get_data()).get("education_group")

    else:
        await message.delete()
        education_group = message.text.upper()
        if education_group not in edu_groups:
            await bot.edit_message_text(
                "<b>❌ Ошибка. Группа не найдена</b>\n\n"
                "Пожалуйста, напиши свою учебную группу",
                chat_id=from_user.id,
                message_id=(await state.get_data()).get("new_message_id"),
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                    types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_bmstu_edu")
                ]])
            )
            await state.update_data(education_group=None)
            return

        if (await state.get_data()).get("education_group") == education_group:
            return
        await state.update_data(education_group=education_group)

    old_message_id = (await state.get_data()).get("new_message_id")
    if callback is not None:
        old_message_id = callback.message.message_id
    await bot.edit_message_text(
        "<b>Напиши свою учебную группу:</b>\n\n"
        f"<i>&gt; {education_group}</i>",
        chat_id=from_user.id,
        message_id=old_message_id,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_bmstu_edu"),
            types.InlineKeyboardButton(text="▶️ Далее", callback_data="register__after_education_group")
        ]])
    )


@router.callback_query(F.data == "register__after_bmstu_education__no")
async def after_education_group__handler(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[HANDLER] After bmstu education (id={callback.from_user.id})")

    #await state.clear()
    #await callback.message.edit_text('😭 К сожалению, регистрация для студентов других ВУЗов уже закрыта')
    #return

    await state.update_data(bmstu_education=False, passport_data=None)

    new_message = await callback.message.answer(
        'Напиши полное название своего ВУЗа',
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_bmstu_edu")
        ]])
    )
    await callback.message.delete()

    await state.update_data(new_message_id=new_message.message_id)
    await state.set_state(RegistrationForm.university)


@router.message(RegistrationForm.university)
@router.callback_query(F.data == "registration__back_to_university")
async def university__handler(message: Union[types.Message, types.CallbackQuery], bot: Bot, state: FSMContext):
    logger.info(f"[HANDLER] University (id={message.from_user.id})")
    await state.set_state(RegistrationForm.university)

    state_data = await state.get_data()
    from_user = message.from_user
    if isinstance(message, types.CallbackQuery):
        university = state_data.get("university")

    else:
        await message.delete()
        university = message.text
        if state_data.get("university") == university:
            return
        await state.update_data(university=university)


    old_message_id = state_data.get("new_message_id")
    await bot.edit_message_text(
        "<b>Напиши полное название своего ВУЗа:</b>\n\n"
        f"<i>&gt; {university}</i>",
        chat_id=from_user.id,
        message_id=old_message_id,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_bmstu_edu"),
            types.InlineKeyboardButton(text="▶️ Далее", callback_data="register__after_university")
        ]])
    )


@router.callback_query(F.data == "register__after_university")
async def after_education_group__handler(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[HANDLER] After bmstu education (id={callback.from_user.id})")

    await state.update_data(bmstu_education=False, passport_data=None)

    new_message = await callback.message.answer(
        'Напиши серию и номер своего паспорта в формате <code>XXXX YYYYYY</code>',
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_university")
        ]])
    )
    await callback.message.delete()

    await state.update_data(new_message_id=new_message.message_id)
    await state.set_state(RegistrationForm.passport_data)


@router.message(RegistrationForm.passport_data)
@router.callback_query(F.data == "registration__back_to_passport_data")
async def passport_data__handler(message: Union[types.Message, types.CallbackQuery], bot: Bot, state: FSMContext):
    logger.info(f"[HANDLER] Passport data (id={message.from_user.id})")
    await state.set_state(RegistrationForm.passport_data)

    state_data = await state.get_data()
    share_phone_request_message_id = state_data.get("share_phone_request_message_id")
    if share_phone_request_message_id is not None:
        await bot.delete_message(chat_id=message.from_user.id, message_id=share_phone_request_message_id)
        await state.update_data(share_phone_request_message_id=None)

    from_user = message.from_user
    if isinstance(message, types.CallbackQuery):
        passport_data = state_data.get("passport_data")

    else:
        await message.delete()

        passport_data = message.text
        if len(passport_data) > 20:
            try:
                await bot.edit_message_text(
                    "<b>❌ Ошибка.</b>\n\n"
                    "Пожалуйста, напиши серию и номер своего паспорта в формате <code>XXXX YYYYYY</code>",
                    chat_id=from_user.id,
                    message_id=state_data.get("new_message_id"),
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_university"),
                    ]])
                )
            except aiogram.exceptions.TelegramBadRequest:
                pass
            return

        if state_data.get("passport_data") == passport_data:
            return
        await state.update_data(passport_data=passport_data)


    old_message_id = state_data.get("new_message_id")
    await bot.edit_message_text(
        "<b>Напиши серию и номер своего паспорта в формате <code>XXXX YYYYYY</code>:</b>\n\n"
        f"<i>&gt; {passport_data}</i>",
        chat_id=from_user.id,
        message_id=old_message_id,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_university"),
            types.InlineKeyboardButton(text="▶️ Далее", callback_data="register__after_passport_data")
        ]])
    )


@router.callback_query(F.data == "register__after_passport_data")
@router.callback_query(F.data == "register__after_education_group")
async def after_passport_data__handler(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[HANDLER] After passport data (id={callback.from_user.id})")

    back_btn = "registration__back_to_passport_data"
    if (await state.get_data())["bmstu_education"] == True:
        back_btn = "registration__back_to_edu_group"

    new_message = await callback.message.answer(
        'Напиши свой номер телефона',
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Поделиться номером", callback_data="register__show_phone_button")],
            [types.InlineKeyboardButton(text="◀️ Назад", callback_data=back_btn)]
        ])
    )
    await callback.message.delete()

    await state.update_data(new_message_id=new_message.message_id, phone_number=None)
    await state.set_state(RegistrationForm.phone_number)


@router.callback_query(F.data == "register__show_phone_button")
async def show_phone_button__handler(callback: types.CallbackQuery, state: FSMContext):
    new_message = await callback.message.answer(
        'Чтобы поделиться своим номером, нажми кнопку 👇',
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[
                types.KeyboardButton(text="Поделиться номером", request_contact=True)
            ]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

    await state.update_data(share_phone_request_message_id=new_message.message_id)
    await state.set_state(RegistrationForm.phone_number)


@router.message(RegistrationForm.phone_number)
@router.callback_query(F.data == "registration__back_to_phone_number")
async def phone_number__handler(message: Union[types.Message, types.CallbackQuery], bot: Bot, state: FSMContext):
    logger.info(f"[HANDLER] Phone number (id={message.from_user.id})")
    await state.set_state(RegistrationForm.phone_number)

    state_data = await state.get_data()
    old_message_id = state_data.get("new_message_id")
    share_phone_request_message_id = state_data.get("share_phone_request_message_id")
    if share_phone_request_message_id is not None:
        await bot.delete_message(chat_id=message.from_user.id, message_id=share_phone_request_message_id)
        await state.update_data(share_phone_request_message_id=None)

    back_btn = "registration__back_to_passport_data"
    if state_data["bmstu_education"] == True:
        back_btn = "registration__back_to_edu_group"

    from_user = message.from_user
    callback = None
    if isinstance(message, types.CallbackQuery):
        callback = message
        message = callback.message
        phone_number = state_data.get("phone_number")
        await message.delete()

    else:
        await message.delete()

        # TODO: belarus, казахстан, узбекистан phone number
        phone = message.text
        if message.contact is not None:
            phone = message.contact.phone_number
        phone_number = phonenumbers.parse(phone, "RU")
        if not phonenumbers.is_valid_number(phone_number):
            new_message = await message.answer(
                "<b>❌ Ошибка.</b>\n\n"
                "Пожалуйста, напиши свой номер телефона:",
                reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                    [types.InlineKeyboardButton(text="Поделиться номером", callback_data="register__show_phone_button")],
                    [types.InlineKeyboardButton(text="◀️ Назад", callback_data=back_btn)]
                ])
            )
            await bot.delete_message(chat_id=message.from_user.id, message_id=old_message_id)
            await state.update_data(new_message_id=new_message.message_id, phone_number=None)
            return
        phone_number = "+" + str(phone_number.country_code) + str(phone_number.national_number)
        await state.update_data(phone_number=phone_number)

    new_message = await message.answer(
        "<b>Напиши свой номер телефона:</b>\n\n"
        f"<i>&gt; {phone_number}</i>",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Поделиться номером", callback_data="register__show_phone_button")],
            [
                types.InlineKeyboardButton(text="◀️ Назад", callback_data=back_btn),
                types.InlineKeyboardButton(text="▶️ Далее", callback_data="register__after_phone_number")
            ],
        ])
    )
    try:
        await bot.delete_message(chat_id=message.from_user.id, message_id=old_message_id)
    except aiogram.exceptions.TelegramBadRequest:
        pass
    await state.update_data(new_message_id=new_message.message_id)


@router.callback_query(F.data == "register__after_phone_number")
async def after_phone_number__handler(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[HANDLER] After phone number (id={callback.from_user.id})")

    new_message = await callback.message.answer(
        'Напиши свой никнейм, который будет отображаться на трансляции',
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_bmstu_edu")
        ]])
    )
    if not isinstance(callback.message, types.InaccessibleMessage):
        await callback.message.delete()

    await state.update_data(new_message_id=new_message.message_id)
    await state.set_state(RegistrationForm.nickname)


@router.message(RegistrationForm.nickname)
@router.callback_query(F.data == "registration__back_to_nickname")
async def nickname__handler(message: Union[types.Message, types.CallbackQuery], bot: Bot, state: FSMContext):
    logger.info(f"[HANDLER] Nickname (id={message.from_user.id})")
    await state.set_state(RegistrationForm.nickname)
    from_user = message.from_user

    state_data = await state.get_data()
    if isinstance(message, types.CallbackQuery):
        nickname = state_data.get("nickname")

    else:
        await message.delete()

        nickname = message.text
        if len(nickname) > 20:
            try:
                await bot.edit_message_text(
                    "<b>❌ Никнейм слишком длинный</b>\n\n"
                    "Пожалуйста, напиши свой никнейм, который будет отображаться на трансляции",
                    chat_id=from_user.id,
                    message_id=state_data.get("new_message_id"),
                    reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                        types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_phone_number"),
                    ]])
                )
            except aiogram.exceptions.TelegramBadRequest:
                pass
            return

        if state_data.get("nickname") == nickname:
            return
        await state.update_data(nickname=nickname)


    old_message_id = state_data.get("new_message_id")
    await bot.edit_message_text(
        "<b>Напиши свой никнейм, который будет отображаться на трансляции:</b>\n\n"
        f"<i>&gt; {nickname}</i>",
        chat_id=from_user.id,
        message_id=old_message_id,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_phone_number"),
            types.InlineKeyboardButton(text="▶️ Далее", callback_data="register__after_nickname")
        ]])
    )


@router.callback_query(F.data == "register__after_nickname")
async def after_track__finish__handler(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = "<b>Проверка данных:</b>\n<blockquote>"
    text += f"<b>ФИО:</b> {data['full_name']}\n"
    text += f"<b>Дата рождения:</b> {data['birthdate']}\n"
    if data["bmstu_education"]:
        text += f"<b>Учебная группа:</b> {data['education_group']}\n"
    else:
        text += f"<b>ВУЗ:</b> {data['university']}\n"
        text += f"<b>Серия и номер паспорта:</b> {data['passport_data']}\n"
    text += f"<b>Номер телефона:</b> {data['phone_number']}\n"
    text += f"<b>Никнейм:</b> {data['nickname']}\n"
    text += "</blockquote>\nВcё верно?"

    await callback.message.edit_text(
        text=text,
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            # [types.InlineKeyboardButton(text="✏️ Изменить ФИО", callback_data="register__finish_registration")],
            # [types.InlineKeyboardButton(text="✏️ Изменить дату рождения", callback_data="register__finish_registration")],
            # [types.InlineKeyboardButton(text="✏️ Изменить учебную группу", callback_data="register__finish_registration")],
            # [types.InlineKeyboardButton(text="✏️ Изменить данные паспорта", callback_data="register__finish_registration")],
            # [types.InlineKeyboardButton(text="✏️ Изменить номер телефона", callback_data="register__finish_registration")],
            [
                types.InlineKeyboardButton(text="◀️ Назад", callback_data="registration__back_to_nickname"),
                types.InlineKeyboardButton(text="❌ Отмена", callback_data="register__cancel_registration"),
            ],
            [types.InlineKeyboardButton(text="Да", callback_data="register__finish_registration", style="success")],
        ])
    )


@router.callback_query(F.data == "register__cancel_registration")
async def finish_registration__handler(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"[HANDLER] Cancel registration (id={callback.from_user.id})")
    await state.clear()

    await callback.message.answer(
        "❌ Регистрация отменена",
        reply_markup=constants.keyboard.main_keyboard__with_registration
    )
    await callback.message.delete()


@router.callback_query(F.data == "register__finish_registration")
async def finish_registration__handler(callback: types.CallbackQuery, state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] Finish registration (id={callback.from_user.id})")

    data = await state.get_data()
    await state.clear()
    db_registration = await db_session.merge(database.models.registration.Registration(
        tg_user_id=callback.from_user.id,
        full_name=data["full_name"],
        from_bmstu=data["bmstu_education"],
        phone_number=data["phone_number"],
        birthdate=datetime.datetime.strptime(data["birthdate"], "%d.%m.%Y").date(),
        edu_group=data.get("education_group"),
        university=data.get("university"),
        passport_data=data.get("passport_data"),
        nickname=data.get("nickname")
    ))
    await db_session.commit()
    await db_session.refresh(db_registration)

    await callback.message.delete()
    await callback.message.answer(
        "✅ Данные сохранены!\n"
        "Теперь выбирай дисциплины и регистрируйся на них",
        message_effect_id="5046509860389126442",  # 🎉
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="Counter-Strike 2", callback_data="register__discipline_cs2", style="primary"),
            types.InlineKeyboardButton(text="Dota 2", callback_data="register__discipline_dota2", style="danger"),
            types.InlineKeyboardButton(text="EA FC", callback_data="register__discipline_fifa", style="success"),
        ]])
    )

    # await new_message.answer(
    #     "<b>Хочешь участвовать с друзьями?</b>\n"
    #     "Создавай команду и приглашай в неё своих друзей",
    #     reply_markup=constants.keyboard.main_keyboard
    # )
