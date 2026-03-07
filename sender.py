import sqlalchemy

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


if __name__ == "__main__":
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(finish_registration())
