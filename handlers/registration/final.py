from aiogram import types


async def final_message(message: types.Message):
    await message.answer(
        "Вступай в чатик участников: https://t.me/+jhmWZ_xDyUE3YzVi\n"
        "И если у тебя нет своей команды, то вступай в чатик: https://t.me/+WBvVIR88mFViYzFi"
    )

