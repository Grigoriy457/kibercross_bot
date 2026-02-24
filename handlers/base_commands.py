from aiogram import types, Router, Bot, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext

from dispatcher import logger
import constants
import config
import database

from handlers.team import team_join


router = Router()


@router.message(CommandStart())
async def start(message: types.Message, state: FSMContext, bot: Bot, db_session: database.AsyncSession, command: CommandObject = None):
    logger.info(f"[HANDLER] Start command (id={message.from_user.id})")
    await state.clear()

    if (command.args is not None) and command.args.startswith("team_"):
        await team_join.code_message_handler(
            message,
            state=state,
            bot=bot,
            db_session=db_session,
            code=command.args.split("_")[1]
        )
        return

    user = await db_session.merge(database.models.tg.TgUser(id=message.from_user.id, username=message.from_user.username))
    await db_session.commit()

    if (await user.awaitable_attrs.registration) is None:
        reply_markup = constants.keyboard.main_keyboard__with_registration
    else:
        reply_markup = constants.keyboard.main_keyboard

    db_admin = await db_session.scalar(
        database.select(database.models.tg.Admin)
        .where(database.models.tg.Admin.tg_user_id == message.from_user.id)
    )
    if db_admin:
        reply_markup = constants.keyboard.admin_keyboard

    await message.answer('👋 Добро пожаловать на регистрацию «Фиджитал-турнира: Киберкросс»!', reply_markup=reply_markup)


@router.callback_query(F.data == "start__confirm_privacy")
async def start__confirm_privacy(callback: types.CallbackQuery, db_session: database.AsyncSession):
    user = await db_session.merge(database.models.tg.TgUser(
        id=callback.from_user.id,
        username=callback.from_user.username,
        is_policy_confirmed=True
    ))
    await db_session.commit()

    if (await user.awaitable_attrs.registration) is None:
        reply_markup = constants.keyboard.main_keyboard__with_registration
    else:
        reply_markup = constants.keyboard.main_keyboard

    db_admin = await db_session.scalar(
        database.select(database.models.tg.Admin)
        .where(database.models.tg.Admin.tg_user_id == callback.from_user.id)
    )
    if db_admin:
        reply_markup = constants.keyboard.admin_keyboard

    await callback.message.edit_reply_markup()
    await callback.message.answer(
        "✅ Теперь ты можешь зарегистрироваться на «Фиджитал-турнир: Киберкросс»",
        reply_markup=reply_markup
    )


@router.message(Command("info"))
@router.message(F.text == constants.keyboard.keyboard__buttons["info"])
async def info(message: types.Message, state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] Start command (id={message.from_user.id})")
    await state.clear()

    user = await db_session.merge(database.models.tg.TgUser(id=message.from_user.id, username=message.from_user.username))
    await db_session.commit()

    text = 'Что? \n\n'
    text += 'По всем вопросам по поводу мероприятия пиши <a href="https://t.me/sergkpt">Серёже</a>.'

    if (await user.awaitable_attrs.registration) is None:
        reply_markup = constants.keyboard.main_keyboard__with_registration
    else:
        reply_markup = constants.keyboard.main_keyboard
    await message.answer(text, reply_markup=reply_markup)


@router.message(Command("help"))
@router.message(F.text == constants.keyboard.keyboard__buttons["help"])
async def help_handler(message: types.Message, state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] Help command (id={message.from_user.id})")
    await state.clear()

    await db_session.merge(database.models.tg.TgUser(id=message.from_user.id, username=message.from_user.username))
    await db_session.commit()

    await message.answer(
        f"Нашел ошибку или есть вопрос по работе бота, обращайся к <a href='https://t.me/{config.SUPPORT_USERNAME}'>Грише</a>",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="🆘 Помощь", url=f"https://t.me/{config.SUPPORT_USERNAME}")
        ]])
    )


@router.message(Command("id"))
async def id_handler(message: types.Message, state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] ID command (id={message.from_user.id})")
    await state.clear()

    await db_session.merge(database.models.tg.TgUser(id=message.from_user.id, username=message.from_user.username))
    await db_session.commit()

    await message.answer(f"Твой id: <code>{message.from_user.id}</code>")
