import json
import logging
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

from dialogs import MainDialog
from quiz import send_question, factory

from aiogram import Bot, Dispatcher, executor
# from aiogram.contrib.fsm_storage.redis import RedisStorage2
# from aiogram.contrib.middlewares.logging import LoggingMiddleware

from quiz import Question

logging.basicConfig(level=logging.INFO)

TOKEN = "1967422077:AAEAmzvwkvo5azevFSkGobxRMi4bQ48Z5SA"
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
# dp.middleware.setup(LoggingMiddleware())


questions = []
with open("data.json", encoding='utf-8') as f:
    raw_data = json.load(f)
    for q in raw_data:
        questions.append(Question(**q))







@dp.message_handler(commands=["start"], state="*")
async def start(message: types.Message):
    await message.answer("Привет! Как тебя зовут?")
    await MainDialog.enter_name.set()


@dp.message_handler(state=MainDialog.enter_name)
async def enter_name(message: types.Message, state: FSMContext):
    async with state.proxy() as storage:
        storage["name"] = message.text
    await message.answer(f"Приятно познакомиться, {message.text}. А сколько тебе лет?")
    await MainDialog.enter_age.set()


@dp.message_handler(state=MainDialog.enter_age)
async def enter_age(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите корректный возраст")
        return
    if not 1 <= int(float(message.text)) <= 100:
        await message.answer("Введите корректный возраст")
        return
    async with state.proxy() as storage:
        storage["age"] = message.text
        storage["current_question"] = 0
        await message.answer(
            f'Ну что, {storage["name"]} {storage["age"]} лет, начнём игру'
        )
        await send_question(
            bot, message.chat.id, questions[storage["current_question"]]
        )
    await MainDialog.quiz.set()


@dp.message_handler(state=MainDialog.quiz)
@dp.callback_query_handler(factory.filter(), state=MainDialog.quiz)
async def quiz_process2(obj, state: FSMContext, callback_data: dict = None):
    async with state.proxy() as storage:
        current_question = questions[storage["current_question"]]
        if isinstance(obj, types.Message):
            if obj.text not in current_question.answers:
                await obj.answer("Выберите один из предложенных ответов")
                return
            chat_id = obj.chat.id
            if not current_question.is_right(obj.text):
                await obj.answer("Неправильный ответ, попробуйте еще раз")
                return
        else:
            await obj.answer(text="Ответ принят!")
            chat_id = obj.message.chat.id
            if not current_question.is_right_by_index(int(callback_data["number"])):
                await bot.send_message(
                    chat_id, text="Неправильный ответ, попробуйте еще раз"
                )
                return
        await bot.send_message(
            chat_id,
            text="Верно! Ответишь на следующий?",
            reply_markup=types.ReplyKeyboardRemove(),
        )
        storage["current_question"] += 1
        if storage["current_question"] >= len(questions):
            await bot.send_message(
                chat_id,
                "Ой, вопросы для вас закончились, приходите завтра или пройдите заново, нажав /start",
                reply_markup=types.ReplyKeyboardRemove(),
            )
            await MainDialog.win.set()
            return
        await send_question(bot, chat_id, questions[storage["current_question"]])


@dp.message_handler(state=MainDialog.win)
async def win(message: types.Message):
    await bot.send_message(
        message.chat.id,
        text="Ой, вопросы для вас закончились, приходите завтра или пройдите заново, нажав /start",
    )











if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
