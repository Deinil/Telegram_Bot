import logging
import sqlite3
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import exceptions, executor
import schedule

logging.basicConfig(level=logging.INFO)

bot = Bot(token='YOUR_TOKEN')
dp = Dispatcher(bot)

# Connect to SQLite database
conn = sqlite3.connect('notifications.db', check_same_thread=False)
cursor = conn.cursor()

# Create table for notifications if it doesn't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    text TEXT NOT NULL,
                    time TEXT NOT NULL,
                    days TEXT NOT NULL)''')
conn.commit()


# Define function to create new notification
async def create_notification(message):
    user_id = message.from_user.id
    text = message.text.split(' ', 1)[1]
    time = text.split(' ')[0]
    days = text.split(' ')[1:]
    days_str = ' '.join(days)
    cursor.execute("INSERT INTO notifications (user_id, text, time, days) VALUES (?, ?, ?, ?)",
                   (user_id, text, time, days_str))
    conn.commit()
    await bot.send_message(chat_id=message.chat.id,
                           text=f"Оповещение успешно создано на {days_str} в {time}.",
                           parse_mode=ParseMode.HTML)


# Define function to show all notifications for a user
async def show_notifications(message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM notifications WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    if len(rows) == 0:
        await bot.send_message(chat_id=message.chat.id,
                               text="У вас нет созданных оповещений.",
                               parse_mode=ParseMode.HTML)
        return

    response_text = "<b>Ваши оповещения:</b>\n\n"
    for row in rows:
        response_text += f"<b>ID:</b> {row[0]}\n<b>Время:</b> {row[3]}\n<b>Дни недели:</b> {row[4]}\n<b>Текст:</b> {row[2]}\n\n"

    await bot.send_message(chat_id=message.chat.id,
                           text=response_text,
                           parse_mode=ParseMode.HTML)


# Define function to edit an existing notification for a user
async def edit_notification(message):
    user_id = message.from_user.id
    notification_id = message.text.split(' ')[1]
    new_text = message.text.split(' ', 2)[2]

    cursor.execute("SELECT * FROM notifications WHERE id=? AND user_id=?", (notification_id, user_id))
    row = cursor.fetchone()

    if row is None:
        await bot.send_message(chat_id=message.chat.id,
                               text="Вы не можете редактировать это оповещение.",
                               parse_mode=ParseMode.HTML)
        return

    cursor.execute("UPDATE notifications SET text=? WHERE id=?", (new_text, notification_id))
    conn.commit()

    await bot.send_message(chat_id=message.chat.id,
                           text="Оповещение успешно отредактировано.",
                           parse_mode=ParseMode.HTML)


# Start the bot and add handlers for commands and messages
@dp.message_handler(commands=['start'])
async def start(message):
    await bot.send_message(chat_id=message.chat.id,
                           text="Привет! Я бот для создания и управления оповещениями. Используйте команду /help для получения списка доступных команд.",
                           parse_mode=ParseMode.HTML)


@dp.message_handler(commands=['help'])
async def help(message):
    help_text = "<b>Список доступных команд:</b>\n\n"
    help_text += "/create - Создать новое оповещение.\n"
    help_text += "/show - Показать все созданные оповещения.\n"
    help_text += "/edit <i>ID</i> <i>новый текст</i> - Отредактировать существующее оповещение.\n"

    await bot.send_message(chat_id=message.chat.id,
                           text=help_text,
                           parse_mode=ParseMode.HTML)


async def create_notification(message):
    user_id = message.from_user.id
    text = message.text.split(' ', 1)[1]
    time = text.split(' ')[0]
    days = text.split(' ')[1:]
    days_str = ' '.join(days)
    cursor.execute("INSERT INTO notifications (user_id, text, time, days) VALUES (?, ?, ?, ?)",
                   (user_id, text, time, days_str))
    conn.commit()
    await bot.send_message(chat_id=message.chat.id,
                           text=f"Оповещение успешно создано на {days_str} в {time}.",
                           parse_mode=ParseMode.HTML)


async def show_notifications(message):
    user_id = message.from_user.id
    cursor.execute("SELECT * FROM notifications WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()
    if len(rows) == 0:
        await bot.send_message(chat_id=message.chat.id,
                               text="У вас нет созданных оповещений.",
                               parse_mode=ParseMode.HTML)
        return

    response_text = "<b>Ваши оповещения:</b>\n\n"
    for row in rows:
        response_text += f"<b>ID:</b> {row[0]}\n<b>Время:</b> {row[3]}\n<b>Дни недели:</b> {row[4]}\n<b>Текст:</b> {row[2]}\n\n"

    await bot.send_message(chat_id=message.chat.id,
                           text=response_text,
                           parse_mode=ParseMode.HTML)


async def edit_notification(message):
    user_id = message.from_user.id
    notification_id = message.text.split(' ')[1]
    new_text = message.text.split(' ', 2)[2]

    cursor.execute("SELECT * FROM notifications WHERE id=? AND user_id=?", (notification_id, user_id))
    row = cursor.fetchone()

    if row is None:
        await bot.send_message(chat_id=message.chat.id,
                               text="Вы не можете редактировать это оповещение.",
                               parse_mode=ParseMode.HTML)
        return

    cursor.execute("UPDATE notifications SET text=? WHERE id=?", (new_text, notification_id))
    conn.commit()

    await bot.send_message(chat_id=message.chat.id,
                           text="Оповещение успешно отредактировано.",
                           parse_mode=ParseMode.HTML)


async def send_notifications():
    now = datetime.now()
    current_time = now.strftime("%H:%M")
    current_day = now.strftime("%A").lower()

    cursor.execute("SELECT * FROM notifications WHERE time=? AND days LIKE ?", (current_time, f"%{current_day}%"))
    rows = cursor.fetchall()

    for row in rows:
        try:
            await bot.send_message(chat_id=row[1], text=row[2])
        except exceptions.BotBlocked:
            print(f"Target [ID:{row[1]}] blocked the bot.")
        except exceptions.ChatNotFound:
            print(f"Chat not found [ID:{row[1]}].")
        except exceptions.RetryAfter as e:
            print(f"Rate limited. Sleep {e.timeout} seconds.")
            await asyncio.sleep(e.timeout)
            return await send_notifications()
        except exceptions.TelegramAPIError:
            print(f"Failed to send notification to [ID:{row[1]}].")


schedule.every(10).seconds.do(send_notifications)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)

