import datetime

import sqlalchemy
from aiogram import types

import constants.keyboard
import database
from dispatcher import bot


PARTICIPANTS_CHAT_ID = -1003846680129



async def channel_invite():
    async with database.Database() as db:
        async with db.session() as session:
            registrations = (await session.scalars(
                database.select(database.models.registration.Registration)
                .where(sqlalchemy.or_(
                    database.models.registration.Registration.discipline_cs2 == True,
                    database.models.registration.Registration.discipline_dota2 == True,
                    database.models.registration.Registration.discipline_fifa == True
                ))
            )).all()
            k = len(registrations)
            counter = 0
            for i, registration in enumerate(registrations):
                print(f"{i + 1}/{k} - {registration.tg_user_id}")
                if (member := await bot.get_chat_member(PARTICIPANTS_CHAT_ID, registration.tg_user_id)) is not None and member.status == "member":
                    await asyncio.sleep(1 / 30)
                    continue
                counter += 1
                try:
                    await bot.send_message(
                        registration.tg_user_id,
                        "<tg-emoji emoji-id='5472055112702629499'>👋</tg-emoji> Привет! "
                        "Напоминаем, что турнир скоро начнётся, а ты ещё не вступил в группу. Пожалуйста, вступи в группу, чтобы не пропустить важные объявления и новости о турнире!\n\n"
                        "Ссылка на группу: https://t.me/+SlkDHzPhyNIwZTZi",
                    )
                except Exception as e:
                    print(f"Error for {registration.tg_user_id}: {e}")
                await asyncio.sleep(1 / 15)
            print("SENDED:", counter)



async def finish_registration():
    async with database.Database() as db:
        async with db.session() as session:
            registrations = (await session.scalars(
                database.select(database.models.registration.Registration)
                .where(sqlalchemy.and_(
                    database.models.registration.Registration.discipline_cs2 == False,
                    database.models.registration.Registration.discipline_dota2 == False,
                    database.models.registration.Registration.discipline_fifa == False
                ))
            )).all()
            k = len(registrations)
            for i, registration in enumerate(registrations):
                print(f"{i + 1}/{k} - {registration.tg_user_id}")
                try:
                    await bot.send_message(
                        registration.tg_user_id,
                        "<tg-emoji emoji-id='5472055112702629499'>👋</tg-emoji> Привет! "
                        "Увидели, что ты не закончил регистрацию на турнир\n\n"
                        "Ты можешь зарегистрироваться на дисциплины нажав на кнопку \"🕹 Моя регистрация\". Не упусти шанс поучаствовать в турнире!\n\n",
                        reply_markup=constants.keyboard.main_keyboard
                    )
                except Exception as e:
                    print(f"Error for {registration.tg_user_id}: {e}")
                await asyncio.sleep(1 / 30)


async def less_than_five_in_team():
    async with database.Database() as db:
        async with db.session() as session:
            teams = (await session.scalars(
                database.select(database.models.registration.Team)
                .where(
                    sqlalchemy.select(sqlalchemy.func.count())
                    .select_from(database.models.registration.TeamMembers)
                    .where(database.models.registration.TeamMembers.team_id == database.models.registration.Team.id)
                    .correlate(database.models.registration.Team).as_scalar()
                 < 5)
            )).all()
            k = len(teams)
            for i, team in enumerate(teams):
                print(f"{i + 1}/{k} - {team.title} ({team.discipline})")
                owner_registration = await team.awaitable_attrs.owner_registration
                try:
                    await bot.send_message(
                        await owner_registration.awaitable_attrs.tg_user_id,
                        "<tg-emoji emoji-id='5472055112702629499'>👋</tg-emoji> Привет! "
                        f"Увидели, что в твоей команде \"{team.title}\" по дисциплине {dict(constants.DISCIPLINES)[f'discipline_{team.discipline.name.lower()}']} меньше 5 участников.\n\n"
                        "Постарайтесь набрать 5 участников или организаторам придётся вас объединить с другой командой!\n\n",
                    )
                except Exception as e:
                    print(f"Error for {owner_registration.tg_user_id}: {e}")
                await asyncio.sleep(1 / 30)


async def select_preferred_date_in_team():
    dates = {
        database.models.registration.DisciplineEnum.CS2: [
            datetime.date(2026, 3, 19), datetime.date(2026, 3, 20)
        ],
        database.models.registration.DisciplineEnum.DOTA2: [
            datetime.date(2026, 3, 16), datetime.date(2026, 3, 17)
        ],
        database.models.registration.DisciplineEnum.FIFA: [
            datetime.date(2026, 3, 11), datetime.date(2026, 3, 13)
        ],
    }
    async with database.Database() as db:
        async with db.session() as session:
            teams = (await session.scalars(
                database.select(database.models.registration.Team)
                .where(database.models.registration.Team.preferred_dates == None)
            )).all()
            k = len(teams)
            for i, team in enumerate(teams):
                print(f"{i + 1}/{k} - {team.title} ({team.discipline})")
                owner_registration = await team.awaitable_attrs.owner_registration
                try:
                    buttons = [
                        types.InlineKeyboardButton(
                            text=date.strftime("%d.%m.%Y"),
                            callback_data=f"for_sender__select_date__{team.id}__{date.isoformat()}"
                        )
                        for date in dates[team.discipline]
                    ] + [
                        types.InlineKeyboardButton(
                            text="Любая",
                            callback_data=f"for_sender__select_date__{team.id}__any"
                        )
                    ]
                    await bot.send_message(
                        await owner_registration.awaitable_attrs.tg_user_id,
                        "<tg-emoji emoji-id='5472055112702629499'>👋</tg-emoji> Привет! "
                        f"Турнир уже совсем скоро, поэтому выбери предпочитаемую дату, в которую твоя команда \"{team.title}\" по дисциплине {dict(constants.DISCIPLINES)[f'discipline_{team.discipline.name.lower()}']} может играть. "
                        f"Если можете в любую дату, то выбери соответствующий вариант.",
                        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[buttons])
                    )
                except Exception as e:
                    print(f"Error for {owner_registration.tg_user_id}: {e}")
                await asyncio.sleep(1 / 30)


if __name__ == "__main__":
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(select_preferred_date_in_team())
