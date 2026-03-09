from aiogram import types, Router, Bot, F
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.fsm.context import FSMContext
import sqlalchemy

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

    text = '<tg-emoji emoji-id="5291849275783791207">🥶</tg-emoji> <i>Что такое киберкросс?</i>\n'\
           ' — Киберкросс это фиджитал-турнир, на котором будут такие дисциплины, как: Counter-Strike 2, Dota 2 и EA FC, '\
            'а второй этап в реальном мире: лазертаг, тактическая игра «Physical Dota» и мини-футбол соответственно!\n\n'\
           '<tg-emoji emoji-id="5429451923344347143">🎮</tg-emoji> Турнир будет проходить с 9 по 22 марта. '\
           'Дисциплины будут идти линейно, так что ты сможешь зарегистрироваться на все!\n\n'\
           '<tg-emoji emoji-id="5415965335192883624">⚔️</tg-emoji> Скорее регистрируйся и создавай команды, чтобы победить и занять первое место!\n\n'\
           'Ответственные за дисциплины:\n'\
           'CS2 — <a href="t.me/XxxtooNN">Дима</a>\n'\
           'Dota 2 — <a href="t.me/i1_yes">Ваня</a>\n'\
           'EA FC — <a href="t.me/toster0">Егор</a>\n'\
           'Им можно задать вопросы по дисциплинам.\n\n'\
           'По всем остальным вопросам обращайся к <a href="t.me/sergkpt">Серёже</a> — главному организатору.'

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


@router.message(Command("stats"), F.chat.id == config.ADMIN_CHAT_ID)
async def stats_handler(message: types.Message, state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] Stats command (id={message.from_user.id})")
    await state.clear()

    registrations_count = await db_session.scalar(
        sqlalchemy.select(sqlalchemy.func.count()).select_from(database.models.registration.Registration)
    )
    registrations_going_to_open_count = await db_session.scalar(
        sqlalchemy.select(sqlalchemy.func.count()).select_from(database.models.registration.Registration)
        .where(database.models.registration.Registration.is_going_to_open == True)
    )
    registrations_not_going_to_open_count = await db_session.scalar(
        sqlalchemy.select(sqlalchemy.func.count()).select_from(database.models.registration.Registration)
        .where(database.models.registration.Registration.is_going_to_open == False)
    )
    registration_with_disciplines_count = await db_session.scalar(
        sqlalchemy.select(sqlalchemy.func.count()).select_from(database.models.registration.Registration)
        .where(
            sqlalchemy.or_(
                database.models.registration.Registration.discipline_cs2 == True,
                database.models.registration.Registration.discipline_dota2 == True,
                database.models.registration.Registration.discipline_fifa == True
            )
        )
    )
    registrations_cs2_count = await db_session.scalar(
        sqlalchemy.select(sqlalchemy.func.count()).select_from(database.models.registration.Registration)
        .where(database.models.registration.Registration.discipline_cs2 == True)
    )
    registrations_dota2_count = await db_session.scalar(
        sqlalchemy.select(sqlalchemy.func.count()).select_from(database.models.registration.Registration)
        .where(database.models.registration.Registration.discipline_dota2 == True)
    )
    registrations_fifa_count = await db_session.scalar(
        sqlalchemy.select(sqlalchemy.func.count()).select_from(database.models.registration.Registration)
        .where(database.models.registration.Registration.discipline_fifa == True)
    )

    teams_count = await db_session.scalar(
        sqlalchemy.select(sqlalchemy.func.count()).select_from(database.models.registration.Team)
    )
    teams_cs2_count = await db_session.scalar(
        sqlalchemy.select(sqlalchemy.func.count()).select_from(database.models.registration.Team)
        .where(database.models.registration.Team.discipline == database.models.registration.DisciplineEnum.CS2)
    )
    teams_dota2_count = await db_session.scalar(
        sqlalchemy.select(sqlalchemy.func.count()).select_from(database.models.registration.Team)
        .where(database.models.registration.Team.discipline == database.models.registration.DisciplineEnum.DOTA2)
    )
    teams_fifa_count = await db_session.scalar(
        sqlalchemy.select(sqlalchemy.func.count()).select_from(database.models.registration.Team)
        .where(database.models.registration.Team.discipline == database.models.registration.DisciplineEnum.FIFA)
    )

    await message.answer(
        f"<tg-emoji emoji-id='5231200819986047254'>📊</tg-emoji> Всего регистраций: <code>{registrations_count}</code>\n\n"
        f"<tg-emoji emoji-id='5415965335192883624'>⚔️</tg-emoji> Придут на открытие: <code>{registrations_going_to_open_count}</code> "
        f"(не пойдут <code>{registrations_not_going_to_open_count}</code>)\n\n"
        f"<tg-emoji emoji-id='5229011542011299168'>👑</tg-emoji> <b>Регистраций с выбранной дисциплиной:</b> <code>{registration_with_disciplines_count}</code>\n"
        f"<tg-emoji emoji-id='5431628883352895287'>🎮</tg-emoji> CS2 — <code>{registrations_cs2_count}</code>\n"
        f"<tg-emoji emoji-id='5404333301034927124'>🎮</tg-emoji> DOTA 2 — <code>{registrations_dota2_count}</code>\n"
        f"<tg-emoji emoji-id='5431699131837985981'>🎮</tg-emoji> FIFA — <code>{registrations_fifa_count}</code>\n\n"
        f"<tg-emoji emoji-id='5325547803936572038'>✨</tg-emoji> <b>Количество команд:</b> <code>{teams_count}</code>\n"
        f"<tg-emoji emoji-id='5431628883352895287'>🎮</tg-emoji> CS2 — <code>{teams_cs2_count}</code>\n"
        f"<tg-emoji emoji-id='5404333301034927124'>🎮</tg-emoji> DOTA 2 — <code>{teams_dota2_count}</code>\n"
        f"<tg-emoji emoji-id='5431699131837985981'>🎮</tg-emoji> FIFA — <code>{teams_fifa_count}</code>\n\n"
    )
