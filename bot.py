import logging
import asyncio
import json
import os
import random
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импортируем нашу базу данных
from database import db

# ============================================================
# ТОКЕН БОТА
# ============================================================
TOKEN = "8242125476:AAFCzCQ6ngl8XiHL1Ax9C4cqylz23NJocus"

# ============================================================
# НАСТРОЙКИ
# ============================================================
QUESTIONS_PER_GAME = 10
DIFFICULTY_POINTS = {
    "easy": 1,
    "medium": 2,
    "hard": 3,
    "expert": 5
}

# ============================================================
# ВОПРОСЫ - ПОЛНАЯ БАЗА
# ============================================================
questions_by_topic = {
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "icon": "✈️",
        "questions": [
            {
                "question": "В каком году был запущен Telegram?",
                "options": ["2011", "2013", "2015", "2017"],
                "correct": 1,
                "difficulty": "medium",
                "explanation": "Telegram был запущен 14 августа 2013 года братьями Дуровыми"
            },
            {
                "question": "Как зовут создателя Telegram?",
                "options": ["Павел Дуров", "Илон Маск", "Марк Цукерберг", "Билл Гейтс"],
                "correct": 0,
                "difficulty": "easy",
                "explanation": "Павел Дуров — российский предприниматель, создатель ВКонтакте и Telegram"
            },
            {
                "question": "Что означает 'MTProto' в Telegram?",
                "options": ["Название протокола", "Имя бота", "Тип стикера", "Вид шифрования"],
                "correct": 0,
                "difficulty": "hard",
                "explanation": "MTProto — это собственный протокол шифрования Telegram"
            },
            {
                "question": "Сколько участников может быть в группе Telegram?",
                "options": ["1000", "10 000", "100 000", "200 000"],
                "correct": 3,
                "difficulty": "medium",
                "explanation": "В группах Telegram может быть до 200 000 участников"
            },
            {
                "question": "Какая страна блокировала Telegram в 2018 году?",
                "options": ["Китай", "Россия", "США", "Германия"],
                "correct": 1,
                "difficulty": "hard",
                "explanation": "Россия блокировала Telegram с 2018 по 2020 год"
            },
            {
                "question": "Какой максимальный размер файла можно отправить в Telegram?",
                "options": ["1 ГБ", "2 ГБ", "4 ГБ", "8 ГБ"],
                "correct": 1,
                "difficulty": "medium",
                "explanation": "Premium用户可以 отправлять файлы до 4 ГБ"
            },
            {
                "question": "Что такое 'секретный чат' в Telegram?",
                "options": ["Чат с паролем", "Чат с шифрованием", "Чат с таймером", "Скрытый чат"],
                "correct": 1,
                "difficulty": "medium",
                "explanation": "Секретные чаты используют end-to-end шифрование"
            },
            {
                "question": "В каком году появились видеозвонки в Telegram?",
                "options": ["2019", "2020", "2021", "2022"],
                "correct": 1,
                "difficulty": "hard",
                "explanation": "Видеозвонки появились в Telegram в 2020 году"
            },
            {
                "question": "Сколько символов может быть в одном сообщении Telegram?",
                "options": ["4096", "8192", "16384", "32768"],
                "correct": 0,
                "difficulty": "hard",
                "explanation": "Стандартное сообщение может содержать до 4096 символов"
            },
            {
                "question": "Какой язык программирования используется для создания ботов Telegram?",
                "options": ["Python", "Java", "C++", "Любой"],
                "correct": 3,
                "difficulty": "easy",
                "explanation": "Можно использовать любой язык с HTTP-запросами"
            },
            {
                "question": "Что такое Telegram Passport?",
                "options": ["Документы", "Пароли", "Верификация", "Стикеры"],
                "correct": 0,
                "difficulty": "hard",
                "explanation": "Passport хранит документы пользователя"
            },
            {
                "question": "Как зовут брата Павла Дурова?",
                "options": ["Алексей", "Николай", "Михаил", "Дмитрий"],
                "correct": 1,
                "difficulty": "hard",
                "explanation": "Николай Дуров — сооснователь Telegram"
            },
            {
                "question": "Сколько пользователей у Telegram в 2025?",
                "options": ["500 млн", "700 млн", "900 млн", "1 млрд"],
                "correct": 2,
                "difficulty": "medium",
                "explanation": "Telegram достиг 900 млн пользователей"
            },
            {
                "question": "Что такое Telegram Premium?",
                "options": ["Платные стикеры", "Больше функций", "Без рекламы", "Всё вышеперечисленное"],
                "correct": 3,
                "difficulty": "easy",
                "explanation": "Premium дает много дополнительных возможностей"
            },
            {
                "question": "В какой стране зарегистрирован Telegram?",
                "options": ["Россия", "США", "ОАЭ", "Великобритания"],
                "correct": 2,
                "difficulty": "medium",
                "explanation": "Штаб-квартира Telegram в Дубае"
            }
        ]
    },
    "math": {
        "name": "🧮 Математика",
        "emoji": "🧮",
        "icon": "🔢",
        "questions": [
            {
                "question": "Сколько будет 15 × 12?",
                "options": ["160", "170", "180", "190"],
                "correct": 2,
                "difficulty": "easy",
                "explanation": "15 × 12 = 180 (15 × 10 = 150, 15 × 2 = 30, 150 + 30 = 180)"
            },
            {
                "question": "Чему равен квадратный корень из 144?",
                "options": ["10", "11", "12", "13"],
                "correct": 2,
                "difficulty": "easy",
                "explanation": "√144 = 12, потому что 12 × 12 = 144"
            },
            {
                "question": "Сколько градусов в прямом угле?",
                "options": ["45°", "60°", "90°", "180°"],
                "correct": 2,
                "difficulty": "easy",
                "explanation": "Прямой угол равен 90 градусам"
            },
            {
                "question": "Чему равно число π (пи) с точностью до двух знаков?",
                "options": ["3.14", "3.16", "3.18", "3.12"],
                "correct": 0,
                "difficulty": "medium",
                "explanation": "π ≈ 3.14159... поэтому округленно 3.14"
            },
            {
                "question": "Сколько будет 25% от 200?",
                "options": ["25", "50", "75", "100"],
                "correct": 1,
                "difficulty": "easy",
                "explanation": "25% = 1/4, 200 ÷ 4 = 50"
            },
            {
                "question": "Чему равен квадрат числа 13?",
                "options": ["139", "149", "159", "169"],
                "correct": 3,
                "difficulty": "easy",
                "explanation": "13 × 13 = 169"
            },
            {
                "question": "Сколько будет 7 × 8?",
                "options": ["48", "56", "64", "72"],
                "correct": 1,
                "difficulty": "easy",
                "explanation": "7 × 8 = 56"
            },
            {
                "question": "Чему равен куб числа 5?",
                "options": ["15", "25", "125", "625"],
                "correct": 2,
                "difficulty": "medium",
                "explanation": "5 × 5 × 5 = 125"
            },
            {
                "question": "Сколько будет 123 + 456?",
                "options": ["569", "579", "589", "599"],
                "correct": 1,
                "difficulty": "easy",
                "explanation": "123 + 456 = 579"
            },
            {
                "question": "Чему равно 2 в десятой степени?",
                "options": ["512", "1024", "2048", "4096"],
                "correct": 1,
                "difficulty": "medium",
                "explanation": "2^10 = 1024"
            },
            {
                "question": "Решите уравнение: x + 15 = 30",
                "options": ["x = 5", "x = 10", "x = 15", "x = 20"],
                "correct": 2,
                "difficulty": "easy",
                "explanation": "x = 30 - 15 = 15"
            },
            {
                "question": "Сколько будет 99 - 27?",
                "options": ["62", "72", "82", "92"],
                "correct": 1,
                "difficulty": "easy",
                "explanation": "99 - 27 = 72"
            },
            {
                "question": "Чему равно 3/4 от 100?",
                "options": ["25", "50", "75", "80"],
                "correct": 2,
                "difficulty": "medium",
                "explanation": "100 ÷ 4 × 3 = 75"
            },
            {
                "question": "Сколько сантиметров в метре?",
                "options": ["10", "100", "1000", "10000"],
                "correct": 1,
                "difficulty": "easy",
                "explanation": "1 м = 100 см"
            },
            {
                "question": "Чему равна площадь квадрата со стороной 6 см?",
                "options": ["12", "24", "36", "48"],
                "correct": 2,
                "difficulty": "easy",
                "explanation": "S = 6 × 6 = 36 см²"
            }
        ]
    },
    "tiktok": {
        "name": "🎵 TikTok",
        "emoji": "🎵",
        "icon": "📱",
        "questions": [
            {
                "question": "В каком году TikTok стал мировым феноменом?",
                "options": ["2016", "2018", "2020", "2022"],
                "correct": 1,
                "difficulty": "medium",
                "explanation": "TikTok (Douyin) был запущен в 2016, но мировая популярность пришла в 2018"
            },
            {
                "question": "Какое максимальное время видео в TikTok?",
                "options": ["60 сек", "3 мин", "10 мин", "15 мин"],
                "correct": 2,
                "difficulty": "easy",
                "explanation": "Сейчас можно загружать видео до 10 минут"
            },
            {
                "question": "Что такое 'дуэт' в TikTok?",
                "options": ["Песня", "Совместное видео", "Стикер", "Фильтр"],
                "correct": 1,
                "difficulty": "medium",
                "explanation": "Duet позволяет записать видео рядом с другим видео"
            },
            {
                "question": "Какая самая популярная категория в TikTok?",
                "options": ["Танцы", "Юмор", "Еда", "Образование"],
                "correct": 0,
                "difficulty": "easy",
                "explanation": "Танцевальные видео — самая популярная категория"
            },
            {
                "question": "Сколько пользователей у TikTok в 2026?",
                "options": ["1 млрд", "1.5 млрд", "2 млрд", "2.5 млрд"],
                "correct": 2,
                "difficulty": "hard",
                "explanation": "По прогнозам, в 2026 году у TikTok более 2 миллиардов пользователей"
            },
            {
                "question": "Кто самый популярный тиктокер в мире?",
                "options": ["Charli D'Amelio", "Khaby Lame", "Bella Poarch", "Addison Rae"],
                "correct": 1,
                "difficulty": "hard",
                "explanation": "Khaby Lame — самый популярный с более 160 млн подписчиков"
            },
            {
                "question": "Что такое TikTok Challenges?",
                "options": ["Конкурсы", "Челленджи", "Игры", "Викторины"],
                "correct": 1,
                "difficulty": "easy",
                "explanation": "Это популярные задания, которые повторяют пользователи"
            },
            {
                "question": "Какая страна запустила TikTok?",
                "options": ["США", "Россия", "Китай", "Япония"],
                "correct": 2,
                "difficulty": "medium",
                "explanation": "TikTok создан китайской компанией ByteDance"
            },
            {
                "question": "Как называются короткие видео в TikTok?",
                "options": ["Ролики", "Клипы", "Видео", "Тиктоки"],
                "correct": 0,
                "difficulty": "easy",
                "explanation": "Их часто называют просто роликами"
            },
            {
                "question": "Что такое TikTok Live?",
                "options": ["Прямой эфир", "Запись", "Чат", "Игра"],
                "correct": 0,
                "difficulty": "easy",
                "explanation": "Live — это прямые трансляции"
            },
            {
                "question": "Какая музыка чаще всего используется в TikTok?",
                "options": ["Поп", "Рэп", "Хип-хоп", "Все жанры"],
                "correct": 3,
                "difficulty": "medium",
                "explanation": "В TikTok используют музыку всех жанров"
            },
            {
                "question": "Сколько лайков может набрать популярное видео?",
                "options": ["1 млн", "10 млн", "50 млн", "100 млн"],
                "correct": 3,
                "difficulty": "medium",
                "explanation": "Рекордные видео набирают более 100 млн лайков"
            },
            {
                "question": "Что такое TikTok FYP?",
                "options": ["Рекомендации", "Тренды", "Новинки", "Избранное"],
                "correct": 0,
                "difficulty": "hard",
                "explanation": "For You Page — лента рекомендаций"
            },
            {
                "question": "Кто такой Khaby Lame?",
                "options": ["Певец", "Актер", "Тиктокер", "Режиссер"],
                "correct": 2,
                "difficulty": "easy",
                "explanation": "Khaby Lame — самый популярный тиктокер"
            },
            {
                "question": "Какой танец стал вирусным в 2020?",
                "options": ["Renegade", "Savage", "Blinding Lights", "WAP"],
                "correct": 0,
                "difficulty": "hard",
                "explanation": "Renegade стал первым массовым трендом TikTok"
            }
        ]
    },
    "music2026": {
        "name": "🎸 Музыка 2026",
        "emoji": "🎸",
        "icon": "🎤",
        "questions": [
            {
                "question": "Кто был самым прослушиваемым артистом 2025 года?",
                "options": ["Taylor Swift", "The Weeknd", "Bad Bunny", "Drake"],
                "correct": 0,
                "difficulty": "medium",
                "explanation": "Taylor Swift стала артисткой года с альбомом 'The Tortured Poets Department'"
            },
            {
                "question": "Какой жанр стал самым популярным в 2026?",
                "options": ["Поп", "Хип-хоп", "Электроника", "K-Pop"],
                "correct": 3,
                "difficulty": "hard",
                "explanation": "K-Pop продолжает захватывать мир, BTS и NewJeans лидируют"
            },
            {
                "question": "Какой музыкальный фестиваль собрал больше всего зрителей в 2025?",
                "options": ["Coachella", "Tomorrowland", "Гластонбери", "Lollapalooza"],
                "correct": 1,
                "difficulty": "hard",
                "explanation": "Tomorrowland в Бельгии собрал рекордные 400 000 посетителей"
            },
            {
                "question": "Какая песня стала вирусной в TikTok в 2025?",
                "options": ["Espresso - Sabrina Carpenter", "We Can't Be Friends - Ariana Grande", "Beautiful Things - Benson Boone", "Lose Control - Teddy Swims"],
                "correct": 0,
                "difficulty": "medium",
                "explanation": "Espresso Сабрины Карпентер стала главным хитом лета 2025"
            },
            {
                "question": "Сколько стримов набрал Spotify в 2025?",
                "options": ["100 млрд", "200 млрд", "300 млрд", "400 млрд"],
                "correct": 2,
                "difficulty": "hard",
                "explanation": "В 2025 году на Spotify было прослушано более 300 миллиардов треков"
            },
            {
                "question": "Кто выиграл Грэмми в 2026?",
                "options": ["Taylor Swift", "Billie Eilish", "Olivia Rodrigo", "SZA"],
                "correct": 0,
                "difficulty": "hard",
                "explanation": "Taylor Swift получила Грэмми за альбом года"
            },
            {
                "question": "Какая группа дала самое кассовое турне 2025?",
                "options": ["BTS", "Coldplay", "Ed Sheeran", "Beyoncé"],
                "correct": 1,
                "difficulty": "hard",
                "explanation": "Coldplay собрали более $500 млн в туре Music of the Spheres"
            },
            {
                "question": "Сколько альбомов продала Taylor Swift в 2025?",
                "options": ["5 млн", "10 млн", "15 млн", "20 млн"],
                "correct": 2,
                "difficulty": "hard",
                "explanation": "Только в США было продано более 15 млн копий"
            },
            {
                "question": "Кто стал открытием года в 2025?",
                "options": ["Sabrina Carpenter", "Chappell Roan", "Teddy Swims", "Benson Boone"],
                "correct": 1,
                "difficulty": "medium",
                "explanation": "Chappell Roan стала сенсацией с альбомом 'The Rise and Fall'"
            },
            {
                "question": "Какой стриминговый сервис лидирует в 2026?",
                "options": ["Spotify", "Apple Music", "YouTube Music", "Tidal"],
                "correct": 0,
                "difficulty": "easy",
                "explanation": "Spotify остается лидером с более чем 600 млн пользователей"
            },
            {
                "question": "Кто самый прослушиваемый рэпер 2025?",
                "options": ["Drake", "Kendrick Lamar", "Travis Scott", "21 Savage"],
                "correct": 0,
                "difficulty": "medium",
                "explanation": "Drake остается королем стриминга"
            },
            {
                "question": "Какая песня стала гимном 2025?",
                "options": ["We Can't Be Friends", "Beautiful Things", "Espresso", "Lose Control"],
                "correct": 2,
                "difficulty": "medium",
                "explanation": "Espresso играла везде от TikTok до радио"
            },
            {
                "question": "Сколько концертов дала Taylor Swift в 2025?",
                "options": ["50", "75", "100", "125"],
                "correct": 2,
                "difficulty": "hard",
                "explanation": "Eras Tour продолжился с более чем 100 шоу"
            },
            {
                "question": "Какой альбом был самым ожидаемым в 2025?",
                "options": ["The Tortured Poets Department", "Hurry Up Tomorrow", "Radical Optimism", "Short n' Sweet"],
                "correct": 0,
                "difficulty": "medium",
                "explanation": "Новый альбом Taylor Swift ждали миллионы"
            },
            {
                "question": "Кто победил в номинации 'Лучший новый артист' на Грэмми-2026?",
                "options": ["Sabrina Carpenter", "Chappell Roan", "Teddy Swims", "Victoria Monét"],
                "correct": 1,
                "difficulty": "hard",
                "explanation": "Chappell Roan получила заслуженную награду"
            }
        ]
    }
}

# ============================================================
# НАСТРОЙКА БОТА
# ============================================================
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Хранилище сессий игроков
user_sessions = {}

# ============================================================
# КЛАВИАТУРЫ
# ============================================================
def get_main_keyboard():
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.button(text="📚 Выбрать тему", callback_data="choose_topic")
    builder.button(text="🎲 Случайная тема", callback_data="random_topic")
    builder.button(text="🏆 Таблица лидеров", callback_data="show_leaders")
    builder.button(text="📊 Моя статистика", callback_data="my_stats")
    builder.adjust(2)
    return builder.as_markup()

def get_topics_keyboard():
    """Клавиатура с темами"""
    builder = InlineKeyboardBuilder()
    
    for topic_id, topic in questions_by_topic.items():
        count = len(topic["questions"])
        builder.button(
            text=f"{topic['emoji']} {topic['name']} ({count} вопросов)",
            callback_data=f"topic_{topic_id}"
        )
    
    builder.button(text="◀️ Назад", callback_data="back_to_menu")
    builder.adjust(1)
    return builder.as_markup()

def get_difficulty_keyboard(topic_id):
    """Клавиатура выбора сложности"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🟢 Легко (1 балл)", callback_data=f"diff_{topic_id}_easy")
    builder.button(text="🟡 Средне (2 балла)", callback_data=f"diff_{topic_id}_medium")
    builder.button(text="🟠 Сложно (3 балла)", callback_data=f"diff_{topic_id}_hard")
    builder.button(text="🔴 Эксперт (5 баллов)", callback_data=f"diff_{topic_id}_expert")
    builder.button(text="🎲 Все уровни", callback_data=f"diff_{topic_id}_all")
    builder.button(text="◀️ Назад", callback_data="choose_topic")
    builder.adjust(1)
    return builder.as_markup()

# ============================================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start"""
    # Сохраняем или обновляем пользователя в БД
    await db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    welcome_text = (
        "🎯 **МЕГА-ВИКТОРИНА 2026**\n\n"
        f"📚 Всего тем: {len(questions_by_topic)}\n"
        f"📝 Всего вопросов: {sum(len(t['questions']) for t in questions_by_topic.values())}\n"
        "⭐ Система сложности: 1-5 баллов\n"
        "🔄 Вопросы меняются каждый раз\n"
        "🏆 Соревнуйся с другими игроками\n\n"
        "Выбери действие:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "choose_topic")
async def choose_topic(callback: types.CallbackQuery):
    """Выбор темы"""
    await callback.message.edit_text(
        "📚 **Выбери тему:**\n\n"
        f"В каждой игре {QUESTIONS_PER_GAME} вопросов",
        reply_markup=get_topics_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "random_topic")
async def random_topic(callback: types.CallbackQuery):
    """Случайная тема"""
    topic_id = random.choice(list(questions_by_topic.keys()))
    await callback.message.edit_text(
        f"🎲 **Выбрана тема:** {questions_by_topic[topic_id]['name']}\n\n"
        "Теперь выбери уровень сложности:",
        reply_markup=get_difficulty_keyboard(topic_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("topic_"))
async def select_topic(callback: types.CallbackQuery):
    """Выбрана конкретная тема"""
    topic_id = callback.data.replace("topic_", "")
    await callback.message.edit_text(
        f"{questions_by_topic[topic_id]['icon']} **Тема: {questions_by_topic[topic_id]['name']}**\n\n"
        "Выбери уровень сложности:",
        reply_markup=get_difficulty_keyboard(topic_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("diff_"))
async def start_game_with_difficulty(callback: types.CallbackQuery):
    """Начало игры с выбранной сложностью"""
    _, topic_id, difficulty = callback.data.split("_")
    
    # Получаем все вопросы темы
    all_questions = questions_by_topic[topic_id]["questions"].copy()
    
    # Фильтруем по сложности
    if difficulty != "all":
        filtered = [q for q in all_questions if q.get("difficulty", "medium") == difficulty]
    else:
        filtered = all_questions
    
    # Если вопросов меньше, чем нужно, берем все доступные
    if len(filtered) < QUESTIONS_PER_GAME:
        # Если все равно мало, просто берем все что есть
        selected_questions = filtered
    else:
        # Перемешиваем и выбираем случайные 10 вопросов
        random.shuffle(filtered)
        selected_questions = filtered[:QUESTIONS_PER_GAME]
    
    # Создаем сессию
    user_id = callback.from_user.id
    now = datetime.now()
    
    user_sessions[user_id] = {
        "score": 0,
        "question": 0,
        "name": callback.from_user.full_name or f"Игрок_{user_id}",
        "username": callback.from_user.username,
        "topic": topic_id,
        "topic_name": questions_by_topic[topic_id]["name"],
        "questions": selected_questions,
        "total": len(selected_questions),
        "difficulty": difficulty,
        "start_time": now.isoformat(),
        "answers": []
    }
    
    max_score = calculate_max_score(selected_questions)
    
    await callback.message.edit_text(
        f"🎮 **Игра начинается!**\n\n"
        f"📚 Тема: {questions_by_topic[topic_id]['name']}\n"
        f"📝 Вопросов: {len(selected_questions)}\n"
        f"⭐ Макс. очков: {max_score}\n"
        f"🔄 Вопросы выбраны случайно!",
        parse_mode="Markdown"
    )
    await asyncio.sleep(1)
    await send_question(callback.message, user_id)

def calculate_max_score(questions):
    """Подсчет максимально возможных очков"""
    total = 0
    for q in questions:
        diff = q.get("difficulty", "medium")
        total += DIFFICULTY_POINTS.get(diff, 2)
    return total

async def send_question(message: types.Message, user_id: int):
    """Отправка вопроса"""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    q_num = session["question"]
    questions = session["questions"]
    
    if q_num >= len(questions):
        await end_game(message, user_id)
        return
    
    q = questions[q_num]
    points = DIFFICULTY_POINTS.get(q.get("difficulty", "medium"), 2)
    difficulty_emoji = {
        "easy": "🟢",
        "medium": "🟡",
        "hard": "🟠",
        "expert": "🔴"
    }.get(q.get("difficulty", "medium"), "⚪")
    
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(q["options"]):
        builder.button(text=option, callback_data=f"ans_{q_num}_{i}")
    builder.adjust(2)
    
    await message.answer(
        f"❓ **Вопрос {q_num + 1}/{len(questions)}**\n\n"
        f"{q['question']}\n\n"
        f"{difficulty_emoji} Сложность: {q.get('difficulty', 'medium')} (+{points} баллов)",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data.startswith("ans_"))
async def handle_answer(callback: types.CallbackQuery):
    """Обработка ответа"""
    _, q_num, answer_idx = callback.data.split("_")
    q_num = int(q_num)
    answer_idx = int(answer_idx)
    
    user_id = callback.from_user.id
    session = user_sessions.get(user_id)
    
    if not session or session["question"] != q_num:
        await callback.answer("Этот вопрос уже не актуален!")
        return
    
    q = session["questions"][q_num]
    correct = (answer_idx == q["correct"])
    points = DIFFICULTY_POINTS.get(q.get("difficulty", "medium"), 2)
    
    # Сохраняем ответ
    session["answers"].append({
        "question": q["question"],
        "user_answer": q["options"][answer_idx],
        "correct": correct,
        "points_earned": points if correct else 0
    })
    
    if correct:
        session["score"] += points
        await callback.answer(f"✅ ПРАВИЛЬНО! +{points} баллов")
        
        await callback.message.answer(
            f"✨ **Верно!**\n\n"
            f"+{points} баллов\n"
            f"📚 {q['explanation']}",
            parse_mode="Markdown"
        )
    else:
        correct_answer = q["options"][q["correct"]]
        await callback.answer("❌ Неправильно!")
        
        await callback.message.answer(
            f"❌ **Неправильно!**\n\n"
            f"✅ Правильный ответ: **{correct_answer}**\n"
            f"📚 {q['explanation']}",
            parse_mode="Markdown"
        )
    
    session["question"] += 1
    await callback.message.delete()
    await send_question(callback.message, user_id)

async def end_game(message: types.Message, user_id: int):
    """Завершение игры"""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    score = session["score"]
    total_possible = calculate_max_score(session["questions"])
    percentage = (score / total_possible * 100) if total_possible > 0 else 0
    end_time = datetime.now()
    start_time = datetime.fromisoformat(session["start_time"])
    game_duration = (end_time - start_time).total_seconds() / 60  # в минутах
    
    # Сохраняем игру в БД
    await db.save_game({
        "telegram_id": user_id,
        "topic": session["topic_name"],
        "difficulty": session["difficulty"],
        "score": score,
        "max_score": total_possible,
        "percentage": round(percentage, 1),
        "duration": round(game_duration, 1),
        "answers": session.get("answers", [])
    })
    
    # Показываем результат
    result_text = (
        f"🎉 **ИГРА ОКОНЧЕНА!** 🎉\n\n"
        f"📚 Тема: {session['topic_name']}\n"
        f"⭐ Результат: **{score}** из {total_possible}\n"
        f"📊 Точность: **{percentage:.1f}%**\n"
        f"⏰ Время: {game_duration:.1f} минут\n\n"
    )
    
    if percentage >= 80:
        result_text += "🔥 **ФАНТАСТИКА!** Ты настоящий эксперт!\n"
    elif percentage >= 60:
        result_text += "👍 **ОТЛИЧНО!** Очень хороший результат!\n"
    elif percentage >= 40:
        result_text += "👌 **ХОРОШО!** Можно ещё лучше!\n"
    else:
        result_text += "💪 **НЕПЛОХО!** Попробуй ещё раз!\n"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 Другая тема", callback_data="choose_topic")],
            [InlineKeyboardButton(text="🏆 Таблица лидеров", callback_data="show_leaders")],
            [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
            [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_menu")]
        ]
    )
    
    await message.answer(result_text, reply_markup=keyboard, parse_mode="Markdown")
    del user_sessions[user_id]

@dp.callback_query(lambda c: c.data == "show_leaders")
async def show_leaders(callback: types.CallbackQuery):
    """Показать таблицу лидеров"""
    top_players = await db.get_top_players(15)
    
    if not top_players:
        await callback.message.edit_text(
            "🏆 **Таблица лидеров пока пуста**\n\n"
            "Сыграй первую игру и стань первым!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]]
            ),
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    text = "🏆 **ТОП-15 ИГРОКОВ** 🏆\n\n"
    medals = ["🥇", "🥈", "🥉"]
    
    for i, user in enumerate(top_players, 1):
        medal = medals[i-1] if i <= 3 else f"{i}."
        avg = user.total_score // user.games_played if user.games_played > 0 else 0
        avg_time = user.total_time / user.games_played if user.games_played > 0 else 0
        name_display = user.username or user.first_name or f"Игрок_{user.telegram_id}"
        
        text += f"{medal} {name_display}\n"
        text += f"   ⭐ Всего: {user.total_score} | 🎮 Игр: {user.games_played}\n"
        text += f"   📊 Среднее: {avg} | ⏰ {avg_time:.1f} мин/игру\n\n"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Моя статистика", callback_data="my_stats")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "my_stats")
async def my_stats(callback: types.CallbackQuery):
    """Показать статистику игрока"""
    stats = await db.get_user_stats(callback.from_user.id)
    
    if not stats:
        text = "📊 **У тебя пока нет статистики**\n\nСыграй первую игру!"
    else:
        user = stats['user']
        avg = user.total_score // user.games_played if user.games_played > 0 else 0
        avg_time = user.total_time / user.games_played if user.games_played > 0 else 0
        
        text = (
            f"📊 **ТВОЯ СТАТИСТИКА** 📊\n\n"
            f"👤 Имя: {user.first_name or 'Не указано'}\n"
            f"🆔 Username: @{user.username if user.username else 'нет'}\n\n"
            f"🏆 **ОБЩАЯ СТАТИСТИКА:**\n"
            f"├ ⭐ Всего очков: {user.total_score}\n"
            f"├ 🎮 Сыграно игр: {user.games_played}\n"
            f"├ 📊 Средний результат: {avg}\n"
            f"├ 🏆 Лучший результат: {user.best_score}\n"
            f"└ ⏰ Среднее время игры: {avg_time:.1f} мин\n\n"
            f"📅 Зарегистрирован: {user.registered_at.strftime('%d.%m.%Y')}\n"
            f"🕐 Последняя активность: {user.last_activity.strftime('%d.%m.%Y %H:%M')}"
        )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Таблица лидеров", callback_data="show_leaders")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_menu")]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    """Вернуться в главное меню"""
    await callback.message.edit_text(
        "🎯 **Главное меню**\n\nВыбери действие:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

async def main():
    """Запуск бота"""
    # Создаем таблицы в БД
    await db.create_tables()
    
    print("🤖 ЗАПУСК МЕГА-ВИКТОРИНЫ")
    print(f"📚 Тем: {len(questions_by_topic)}")
    print(f"📝 Всего вопросов: {sum(len(t['questions']) for t in questions_by_topic.values())}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
