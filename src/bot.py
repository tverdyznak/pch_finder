from __future__ import annotations

import logging
from asyncio import to_thread, run
from datetime import datetime, timedelta
from os import getenv

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from utils import (
    parse_date,
    find_friday_years,
    format_date_variants,
    search_youtube,
)

TELEGRAM_TOKEN: str = getenv("TELEGRAM_TOKEN", "")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN не установлен в переменных окружения")


class SearchStates(StatesGroup):
    waiting_for_date = State()
    

async def find_pch(date_str: str) -> str:
    """
        Основная логика поиска выпусков по дате
            - date_str: строка с датой в формате YYYY-MM-DD
            - возвращает строку с результатами поиска, готовую для отправки юзеру
        
        Если за дату не нашлось видео, тогда в радиусе 3х дней ищем другие выпуски
    """

    try:
        input_date = parse_date(date_str)
    except ValueError as c:
        return f"❌ Ошибка: {c}"

    friday_years = find_friday_years(input_date)

    if not friday_years:
        return f"❌ Пятницы на дату {date_str} не найдены в диапазоне {input_date.year}-{input_date.year}" 

    result_text = (
        f"📅 Найдены года с пятницами на {input_date.strftime('%d.%m')}: "
        f"{', '.join(map(str, friday_years))}\n\n"
        "🔍 Ищу видео...\n"
    )

    for year in friday_years:
        target_date = input_date.replace(year=year)
        date_str_formatted = target_date.isoformat() 
        
        for date_variant in format_date_variants(target_date):
            query = f"Поле Чудес {date_variant}"
            result = await to_thread(search_youtube, query)
            
            if result:
                return (
                    result_text
                    + f"\n✅ Найдено видео за {date_str_formatted}:\n{result}"
                )

        alt_results: list[tuple[str, str]] = []
        
        for delta in (-3, 3):
            alt_date = target_date + timedelta(days=delta)
            alt_date_str = alt_date.isoformat()
            
            for date_variant in format_date_variants(alt_date):
                query = f"Поле Чудес {date_variant}"
                result = await to_thread(search_youtube, query)
                
                if result:
                    alt_results.append((alt_date_str, result))
                    break

        if alt_results:
            msg = (
                result_text
                + f"\n🔁 Не найдено видео за {date_str_formatted}. "
                "Предлагаю выпуски рядом с датой:\n"
            )
            
            for d, url in alt_results:
                msg += f"- {d}: {url}\n"
            return msg

        result_text += f"❌ Видео за {date_str_formatted} не найдено\n"

    result_text += "\n❌ Видео не найдено по всем датам"
    return result_text


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📆 Сегодня")],
            [KeyboardButton(text="📅 Какая-то дата")],
        ],
        resize_keyboard=True,
    )
    
    
async def cmd_start(message: types.Message) -> None:
    await message.answer(
        "Ищу выпуски Поле Чудес\n\n"
        "Выбери нужное действие:",
        reply_markup=get_main_keyboard(),
    )
    
    
async def btn_today(message: types.Message) -> None:
    today = datetime.now().date().isoformat()
    
    await message.answer(
        f"🔄 Ищу выпуски на сегодня ({today})...",
        reply_markup=get_main_keyboard(),
    )

    result = await find_pch(today)
    await message.answer(result, reply_markup=get_main_keyboard())
    
    
async def btn_date(message: types.Message, state: FSMContext) -> None:
    await state.set_state(SearchStates.waiting_for_date)
    await message.answer(
        "📝 Введи дату в формате YYYY-MM-DD\n\n"
        "Пример: 2026-03-07",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    
    
async def process_date_input(message: types.Message, state: FSMContext) -> None:
    date_input = message.text.strip()
    await message.answer(f"🔄 Ищу выпуски на {date_input}...")
    result = await find_pch(date_input)
    await message.answer(result, reply_markup=get_main_keyboard())
    await state.clear()
    
    
async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    bot = Bot(token=TELEGRAM_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Разумеется регаем хэндлеры
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(btn_today, F.text == "📆 Сегодня")
    dp.message.register(btn_date, F.text == "📅 Какая-то дата")
    dp.message.register(process_date_input, SearchStates.waiting_for_date)

    logger.info("🤖 Бот запущен!")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        
        
if __name__ == "__main__":
    run(main())