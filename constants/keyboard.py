from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def keyboard_builder(buttons, position):
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=buttons[button_type])
                for button_type in buttons_type
            ]
            for buttons_type in position],
        resize_keyboard=True,
        selective=True,
        is_persistent=True
    )


keyboard__buttons = {
    "registration": "📝 Регистрация",
    "my_registration": "🕹 Моя регистрация",
    "my_team": "👥 Моя команда",
    "info": "ℹ️ Инфо",
    "help": "🆘 Помощь",
    "admin": "🔅 Админка"
}


main_keyboard__with_registration = keyboard_builder(
    buttons=keyboard__buttons,
    position=[
        ["registration"],
        ["info", "help"]
    ]
)

main_keyboard = keyboard_builder(
    buttons=keyboard__buttons,
    position=[
        ["my_registration", "my_team"],
        ["info", "help"]
    ]
)

admin_keyboard = keyboard_builder(
    buttons=keyboard__buttons,
    position=[["admin"]]
)
