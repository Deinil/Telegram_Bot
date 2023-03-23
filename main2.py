import asyncio
import aiogram
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.types import CallbackQuery
import sqlite3
import aioschedule as schedule
import datetime
from aiogram.dispatcher.filters.state import State, StatesGroup

class Notification(StatesGroup):
    text = State()
    time = State()
    chat = State()
    select = State()
    edit = State()
    new_text = State()
    new_time = State()

bot = Bot(token='YOUR_BOT_TOKEN_HERE')
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Создание базы данных для хранения информации об оповещениях
conn = sqlite3.connect('notifications.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, message TEXT, time TEXT)''')
conn.commit()

# Команда для создания нового оповещения
@dp.message_handler(Command('create'))
async def create_notification(message: types.Message):
    await message.answer('Пожалуйста, напишите текст оповещения:')
    await Notification.text.set()

# Обработка текста оповещения
@dp.message_handler(state=Notification.text)
async def process_text(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['text'] = message.text

    await message.answer('Пожалуйста, укажите время отправки оповещения в формате ЧЧ:ММ:')
    await Notification.next()

# Обработка времени отправки оповещения
@dp.message_handler(state=Notification.time)
async def process_time(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['time'] = message.text

    await message.answer('Пожалуйста, перешлите сообщение из группового чата, в который вы хотите отправлять оповещения:')
    await Notification.chat.set()

# Обработка выбора группового чата для отправки оповещений
@dp.message_handler(state=Notification.chat)
async def process_chat(message: types.Message, state: FSMContext):
    if not message.forward_from_chat or message.forward_from_chat.type != 'supergroup':
        await message.answer('Неверный выбор. Пожалуйста, попробуйте еще раз.')
        return

    chat_id = message.forward_from_chat.id

    # Проверка наличия бота в участниках группового чата
    try:
        await bot.get_chat_member(chat_id, bot.id)
    except:
        await message.answer('Бот не является участником этого группового чата. Пожалуйста, добавьте бота в участники и попробуйте еще раз.')
        return

    async with state.proxy() as data:
        data['chat_id'] = chat_id

# Сохранение информации об оповещении в базе данных
c.execute("INSERT INTO notifications (chat_id, message, time) VALUES (?, ?, ?)", (data['chat_id'], data['text'], data['time']))
conn.commit()

# Добавление задачи для ежедневной отправки оповещения в указанное время
schedule.every().day.at(data['time']).do(send_notification, data['chat_id'], data['text'])

await message.answer(f"Оповещение '{data['text']}' будет отправлено ежедневно в {data['time']} в групповой чат {message.forward_from_chat.title}.")
await state.finish()

async def send_notification(chat_id, text):
    await bot.send_message(chat_id, text)

async def scheduler():
    while True:
        await schedule.run_pending()
        await asyncio.sleep(1)

asyncio.ensure_future(scheduler())

# Команда для просмотра списка созданных оповещений
@dp.message_handler(Command('list'))
async def list_notifications(message: types.Message):
    c.execute("SELECT * FROM notifications WHERE chat_id=?", (message.chat.id,))
    notifications = c.fetchall()

    if not notifications:
        await message.answer('У вас нет созданных оповещений.')
        return

    text = 'Список созданных оповещений:\n\n'
    for notification in notifications:
        text += f"{notification[0]}. {notification[2]} - {notification[3]}\n"

    await message.answer(text)

# Команда для редактирования существующего оповещения
@dp.message_handler(Command('edit'))
async def edit_notification(message: types.Message):
    c.execute("SELECT * FROM notifications WHERE chat_id=?", (message.chat.id,))
    notifications = c.fetchall()

    if not notifications:
        await message.answer('У вас нет созданных оповещений.')
        return

    text = 'Выберите оповещение для редактирования:\n\n'
    for notification in notifications:
        text += f"{notification[0]}. {notification[2]} - {notification[3]}\n"

    await message.answer(text)
    await Notification.select.set()

# Обработка выбора оповещения для редактирования
@dp.message_handler(state=Notification.select)
async def process_select(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['id'] = message.text

    c.execute("SELECT * FROM notifications WHERE id=?", (data['id'],))
    notification = c.fetchone()

    if not notification:
        await message.answer('Оповещение с таким номером не найдено.')
        return

    await message.answer(f"Вы выбрали оповещение '{notification[2]}'. Что вы хотите изменить?\n1. Текст\n2. Время")
    await Notification.edit.set()

# Обработка выбора параметра для редактирования
@dp.message_handler(state=Notification.edit)
async def process_edit(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['edit'] = message.text

    if data['edit'] == '1':
        await message.answer('Пожалуйста, напишите новый текст оповещения:')
        await Notification.new_text.set()
    elif data['edit'] == '2':
        await message.answer('Пожалуйста, укажите новое время отправки оповещения в формате ЧЧ:ММ:')
        await Notification.new_time.set()
    else:
        await message.answer('Неверный выбор. Пожалуйста, попробуйте еще раз.')
        return
# Обработка нового текста оповещения
@dp.message_handler(state=Notification.new_text)
async def process_new_text(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['new_text'] = message.text

    # Обновление информации об оповещении в базе данных
    c.execute("UPDATE notifications SET message=? WHERE id=?", (data['new_text'], data['id']))
    conn.commit()

    await message.answer(f"Текст оповещения обновлен на '{data['new_text']}'.")
    await state.finish()

# Обработка нового времени отправки оповещения
@dp.message_handler(state=Notification.new_time)
async def process_new_time(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['new_time'] = message.text

    # Обновление информации об оповещении в базе данных
    c.execute("UPDATE notifications SET time=? WHERE id=?", (data['new_time'], data['id']))
    conn.commit()

    # Обновление задачи для ежедневной отправки оповещения в новое время
    for job in schedule.jobs:
        if job.job_func.args == (notification[1], notification[2]):
            schedule.cancel_job(job)
            break

    schedule.every().day.at(data['new_time']).do(send_notification, notification[1], notification[2])

    await message.answer(f"Время отправки оповещения обновлено на {data['new_time']}.")
    await state.finish()

# Команда для удаления существующего оповещения
@dp.message_handler(Command('delete'))
async def delete_notification(message: types.Message):
    c.execute("SELECT * FROM notifications WHERE chat_id=?", (message.chat.id,))
    notifications = c.fetchall()

    if not notifications:
        await message.answer('У вас нет созданных оповещений.')
        return

    text = 'Выберите оповещение для удаления:\n\n'
    for notification in notifications:
        text += f"{notification[0]}. {notification[2]} - {notification[3]}\n"

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)