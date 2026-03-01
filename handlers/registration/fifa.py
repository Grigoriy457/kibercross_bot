from aiogram import types, Router, F
from aiogram.fsm.context import FSMContext

import constants.keyboard
from dispatcher import logger
import database

from handlers.registration.final import final_message


router = Router()


@router.callback_query(F.data == "register__discipline_fifa")
async def register__discipline_fifa(callback: types.CallbackQuery, state: FSMContext, db_session: database.AsyncSession):
    logger.info(f"[HANDLER] Fifa registration (id={callback.from_user.id})")

    await callback.message.delete()

    await state.clear()
    db_registration = await db_session.scalar(
        database.select(database.models.registration.Registration)
        .where(database.models.registration.Registration.tg_user_id == callback.from_user.id)
    )
    if db_registration is None:
        await callback.message.edit_text(
            "❌ Ошибка\n\n"
            "Пожалуйста, начни регистрацию заново, нажав на кнопку \"регистрация\"",
            reply_markup=constants.keyboard.main_keyboard__with_registration
        )
        return

    db_registration.discipline_fifa = True
    await db_session.merge(db_registration)
    await db_session.commit()

    await callback.message.answer(
        "✅ Отлично!\n"
        "Теперь ты зарегистрирован на дисциплину EA FC\n\n"
        "<i>Для регистрации на другие дисциплины нажми на кнопку \"моя регистрация\" и добавь её</i>",
        message_effect_id="5046509860389126442",  # 🎉
        reply_markup=constants.keyboard.main_keyboard
    )
    await final_message(callback.message)
