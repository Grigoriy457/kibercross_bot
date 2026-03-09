from aiogram import types, Router, Bot, F
import sqlalchemy
import json
import datetime

import constants
import config
import database


router = Router()


@router.callback_query(F.data.startswith("for_sender__select_date__"))
async def for_sender__select_date(callback: types.CallbackQuery, db_session: database.AsyncSession):
    _, _, team_id, date = callback.data.split("__")

    team = await db_session.get(database.models.registration.Team, int(team_id))

    if date != "any":
        discipline_count = await db_session.scalar(
            database.select(sqlalchemy.func.count())
            .select_from(database.models.registration.Team)
            .where(database.models.registration.Team.discipline == team.discipline)
            .where(database.models.registration.Team.preferred_dates == date)
        )
        conditions = (
            team.discipline == database.models.registration.DisciplineEnum.CS2 and discipline_count > 7,
            team.discipline == database.models.registration.DisciplineEnum.DOTA2 and discipline_count > 5,
            team.discipline == database.models.registration.DisciplineEnum.FIFA and discipline_count > 9,
        )
        if any(conditions):
            await callback.answer(
                "❗️На эту дату уже зарегистрировано слишком много команд, выберите другую. "
                "Если нет возможности, то напишите об этом главному организатору (в разделе \"инфо\" есть его контакт)",
                show_alert=True
            )
            return

    team.preferred_dates = date
    await db_session.merge(team)
    await db_session.commit()

    if date == "any":
        date = "любая"
    else:
        date = datetime.datetime.strptime(date, "%Y-%m-%d").strftime("%d.%m.%Y")
    await callback.message.edit_text(
        f"Дисциплина: {dict(constants.DISCIPLINES)[f'discipline_{team.discipline.name.lower()}']}\n"
        f"Дата: {date}\n\n"
        f"<i>Жди дальнейшую информацию от организаторов турнира.</i>"
    )
