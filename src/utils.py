from __future__ import annotations

import logging
from datetime import datetime
from os import getenv
from re import findall
from sys import stderr
from typing import List, Optional

import requests

try:
    START_YEAR = int(getenv("START_YEAR", "1998"))
    END_YEAR = int(getenv("END_YEAR", "2005"))
except ValueError as e:
    raise RuntimeError("START_YEAR и END_YEAR должны быть целочисленными значениями") from e


def parse_date(date_str: str) -> datetime:
    """
        Парсит строку в формате YYYY-MM-DD в объект datetime
        Отдаёт ValueError, если формат неправильный
    """

    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        raise ValueError(f"Неправильный формат даты, ожидается YYYY-MM-DD: {date_str}") from e
    
    
def find_friday_years(input_date: datetime) -> List[int]:
    """
        Находит все года в заданном диапазоне, когда указанная дата была пятницей
            - input_date: datetime - дата, для которой нужно найти года-пятницы
            - возвращает список годов, когда эта дата была пятницей
        
        Например, для 2000-01-01 функция вернёт все года между START_YEAR и END_YEAR, когда 1 января было пятницей
    """

    friday_years: List[int] = []
    
    for year in range(START_YEAR, END_YEAR + 1):
        try:
            candidate = datetime(year, input_date.month, input_date.day)
        except ValueError:
            logging.debug("Пропускаем кривую дату %02d-%02d для года %d", input_date.month, input_date.day, year,)
            continue

        if candidate.weekday() == 4: # 4 это пятница (ВНЕЗАПНО ДА?)
            friday_years.append(year)

    return friday_years


def format_date_variants(date_obj: datetime) -> List[str]:
    """
        Формируем список вариаций дат для поиска выпуска из date_obj
        Возвращает список вариаций определённой даты
        Наверное можно реализовать лучше, но пока так
    """
    
    return [
        date_obj.strftime("%Y-%m-%d"),  # 2026-03-07
        date_obj.strftime("%d.%m.%Y"),  # 07.03.2026
        date_obj.strftime("%d-%m-%Y"),  # 07-03-2026
        date_obj.strftime("%Y.%m.%d"),  # 2026.03.07
        date_obj.strftime("%d %B %Y"),  # 07 March 2026 (English month)
        date_obj.strftime("%d/%m/%Y"),  # 07/03/2026
        date_obj.strftime("%d.%m"),     # 07.03 (without year)
    ]
    
    
def search_youtube(query: str) -> Optional[str]:
    """
        Осуществляет поиск на YouTube по заданному запросу и возвращает URL первого найденного видео, если оно есть
        (Можно было бы юзать Youtube Data API, но там заёбно)
    """
    
    try:
        search_url = f"https://www.youtube.com/results?search_query={requests.utils.quote(query)}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        response.raise_for_status()
        video_matches = findall(r"/watch\?v=([a-zA-Z0-9_-]{11})", response.text)

        if video_matches:
            return f"https://www.youtube.com/watch?v={video_matches[0]}"

        return None
    except Exception as e:  
        print(f"Ошибка при поиске на YouTube: {e}", file=stderr)
        return None
    