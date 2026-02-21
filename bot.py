import logging
import asyncio
import random
import aiohttp
import html
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import db, pvp_queue

# ============================================================
# ТОКЕН БОТА
# ============================================================
TOKEN = "8242125476:AAFCzCQ6ngl8XiHL1Ax9C4cqylz23NJocus"

# ============================================================
# НАСТРОЙКИ
# ============================================================
QUESTIONS_PER_GAME = 5
PVP_QUESTIONS = 5
DIFFICULTY_POINTS = {
    "easy": 1,
    "medium": 2,
    "hard": 3
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Временные сессии
user_sessions = {}

# ============================================================
# БЕСПЛАТНЫЙ API ДЛЯ ВОПРОСОВ
# ============================================================

async def fetch_trivia_questions(amount=5, category=None, difficulty=None):
    """
    Получает вопросы из бесплатного OpenTDB API
    Не требует API ключа, регистрации или платежей!
    """
    base_url = "https://opentdb.com/api.php"
    params = {
        "amount": amount,
        "type": "multiple",
        "encode": "url3986"
    }
    
    # Категории OpenTDB
    categories = {
        "music": 12,      # Music
        "film": 11,       # Film
        "science": 17,    # Science & Nature
        "math": 19,       # Mathematics
        "history": 23,    # History
        "geography": 22,  # Geography
        "sports": 21,     # Sports
        "animals": 27,    # Animals
        "celebrities": 26 # Celebrities
    }
    
    if category and category in categories:
        params["category"] = categories[category]
    
    if difficulty and difficulty != "all":
        params["difficulty"] = difficulty
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(base_url, params=params, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data["response_code"] == 0:
                        questions = []
                        for item in data["results"]:
                            # Декодируем HTML
                            question = html.unescape(item["question"])
                            correct = html.unescape(item["correct_answer"])
                            incorrect = [html.unescape(x) for x in item["incorrect_answers"]]
                            
                            # Собираем варианты
                            options = [correct] + incorrect
                            random.shuffle(options)
                            correct_index = options.index(correct)
                            
                            questions.append({
                                "question": question,
                                "options": options,
                                "correct": correct_index,
                                "difficulty": item["difficulty"],
                                "explanation": f"📚 Категория: {item['category']}"
                            })
                        return questions
    except Exception as e:
        print(f"API Error: {e}")
        return None

# Маппинг твоих тем на категории API
TOPIC_MAPPING = {
    "telegram": None,
    "math": "math",
    "music2026": "music",
    "tiktok": "celebrities"
}

# ============================================================
# ТВОИ ЛОКАЛЬНЫЕ ВОПРОСЫ
# ============================================================
questions_by_topic = {
    "telegram": {
        "name": "📱 Telegram",
        "emoji": "📱",
        "icon": "✈️",
        "questions": [
            {
                "question": "В каком году запущен Telegram?",
                "options": ["2011", "2013", "2015", "2017"],
                "correct": 1,
                "difficulty": "medium",
                "explanation": "Telegram запущен 14 августа 2013 года"
            },
            {
                "question": "Кто создал Telegram?",
                "options": ["Павел Дуров", "Илон Маск", "Марк Цукерберг", "Билл Гейтс"],
                "correct": 0,
                "difficulty": "easy",
                "explanation": "Павел Дуров — создатель Telegram"
            },
            {
                "question": "Сколько участников может быть в группе?",
                "options": ["1000", "10 000", "100 000", "200 000"],
                "correct": 3,
                "difficulty": "medium",
                "explanation": "До 200 000 участников"
            }
        ]
    },
    "math": {
        "name": "🧮 Математика",
        "emoji": "🧮",
        "icon": "🔢",
        "questions": []
    },
    "tiktok": {
        "name": "🎵 TikTok",
        "emoji": "🎵",
        "icon": "📱",
        "questions": []
    },
    "music2026": {
        "name": "🎸 Музыка 2026",
        "emoji": "🎸",
        "icon": "🎤",
        "questions": []
    }
}

def get_local_questions(topic_id, count=5, difficulty=None):
    """Берёт вопросы из локальной базы"""
    if topic_id not in questions_by_topic:
        return []
        
    all_questions = questions_by_topic[topic_id]["questions"].copy()
    
    if difficulty and difficulty != "all":
        filtered = [q for q in all_questions if q.get("difficulty") == difficulty]
    else:
        filtered = all_questions
    
    if len(filtered) < count:
        filtered = all_questions
    
    random.shuffle(filtered)
    return filtered[:count]

async def get_questions_for_game(topic_id, count=5, difficulty=None):
    """Умная загрузка: API для всех тем кроме Telegram"""
    
    if topic_id == "telegram":
        return get_local_questions(topic_id, count, difficulty)
    
    api_category = TOPIC_MAPPING.get(topic_id)
    if api_category:
        api_questions = await fetch_trivia_questions(
            amount=count,
            category=api_category,
            difficulty=difficulty if difficulty != "all" else None
        )
        if api_questions and len(api_questions) == count:
            return api_questions
    
    return get_local_questions(topic_id, count, difficulty)

# ============================================================
# КНОПКИ
# ============================================================
def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Одиночная игра", callback_data="menu_single")],
        [InlineKeyboardButton(text="👥 PvP Батл", callback_data="menu_pvp")],
        [InlineKeyboardButton(text="🏆 Таблица лидеров", callback_data="menu_leaders")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="menu_stats")]
    ])

def pvp_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Найти соперника", callback_data="pvp_find")],
        [InlineKeyboardButton(text="❌ Покинуть очередь", callback_data="pvp_leave")],
        [InlineKeyboardButton(text="📊 Мои бои", callback_data="pvp_my")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_back")]
    ])

def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="menu_back")]
    ])

def topics_menu():
    builder = InlineKeyboardBuilder()
    for topic_id, topic in questions_by_topic.items():
        builder.button(
            text=f"{topic['emoji']} {topic['name']}",
            callback_data=f"topic_{topic_id}"
        )
    builder.button(text="◀️ Назад", callback_data="menu_back")
    builder.adjust(2)
    return builder.as_markup()

def difficulty_menu(topic_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="🟢 Легко", callback_data=f"diff_{topic_id}_easy")
    builder.button(text="🟡 Средне", callback_data=f"diff_{topic_id}_medium")
    builder.button(text="🔴 Сложно", callback_data=f"diff_{topic_id}_hard")
    builder.button(text="🎲 Всё подряд", callback_data=f"diff_{topic_id}_all")
    builder.button(text="◀️ Назад", callback_data="menu_single")
    builder.adjust(2)
    return builder.as_markup()

# ============================================================
# СТАРТ
# ============================================================
@dp.message(Command("start"))
async def start(message: types.Message):
    await db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )
    await message.answer(
        "🎯 **МЕГА-ВИКТОРИНА**\n\n"
        "📚 4 темы\n"
        "🌍 Тысячи вопросов\n"
        "👥 PvP режим\n"
        "✅ Всё бесплатно!",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

# ============================================================
# МЕНЮ
# ============================================================
@dp.callback_query(F.data == "menu_back")
async def go_back(callback: types.CallbackQuery):
    await callback.message.edit_text("🎯 Главное меню", reply_markup=main_menu())
    await callback.answer()

@dp.callback_query(F.data == "menu_single")
async def menu_single(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📚 **Выбери тему:**",
        reply_markup=topics_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("topic_"))
async def topic_selected(callback: types.CallbackQuery):
    topic_id = callback.data.replace("topic_", "")
    topic = questions_by_topic[topic_id]
    await callback.message.edit_text(
        f"{topic['emoji']} **{topic['name']}**\n\nВыбери сложность:",
        reply_markup=difficulty_menu(topic_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("diff_"))
async def start_single_game(callback: types.CallbackQuery):
    try:
        _, topic_id, difficulty = callback.data.split("_")
    except:
        await callback.answer("Ошибка выбора")
        return
    
    # Получаем вопросы
    game_questions = await get_questions_for_game(
        topic_id=topic_id,
        count=QUESTIONS_PER_GAME,
        difficulty=difficulty
    )
    
    if not game_questions or len(game_questions) == 0:
        await callback.message.edit_text(
            "❌ Не удалось загрузить вопросы. Попробуй позже.",
            reply_markup=back_menu()
        )
        await callback.answer()
        return
    
    uid = callback.from_user.id
    
    user_sessions[uid] = {
        'score': 0,
        'current': 0,
        'questions': game_questions,
        'topic': topic_id,
        'start_time': datetime.now()
    }

    await callback.message.edit_text(
        f"🎮 **Игра начинается!**\n"
        f"📝 Вопросов: {len(game_questions)}",
        parse_mode="Markdown"
    )
    await callback.answer()
    await asyncio.sleep(1)
    await send_single_question(uid)

async def send_single_question(uid):
    """Отправляет следующий вопрос"""
    session = user_sessions.get(uid)
    if not session:
        print(f"Сессия не найдена для {uid}")
        return

    q_idx = session['current']
    
    # Проверяем, не закончилась ли игра
    if q_idx >= len(session['questions']):
        await finish_single_game(uid)
        return

    q = session['questions'][q_idx]
    points = DIFFICULTY_POINTS.get(q.get('difficulty', 'medium'), 2)

    builder = InlineKeyboardBuilder()
    for i, opt in enumerate(q['options']):
        # КОРОТКИЙ callback_data: q{uid}_{q_idx}_{i}
        callback_data = f"q{uid}_{q_idx}_{i}"
        builder.button(text=opt[:20], callback_data=callback_data)
    builder.adjust(2)

    difficulty_emoji = "🟢" if q.get('difficulty') == 'easy' else "🟡" if q.get('difficulty') == 'medium' else "🔴"
    
    try:
        await bot.send_message(
            uid,
            f"❓ **Вопрос {q_idx+1}/{len(session['questions'])}**\n\n"
            f"{q['question']}\n\n"
            f"{difficulty_emoji} {q.get('difficulty', 'medium')} (+{points})",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")

@dp.callback_query(lambda c: c.data and c.data.startswith("q"))
async def single_answer(callback: types.CallbackQuery):
    """Обрабатывает ответ на вопрос"""
    try:
        # Формат: q{uid}_{q_idx}_{i}
        data = callback.data[1:]  # убираем q
        parts = data.split("_")
        
        if len(parts) != 3:
            print(f"Неверный формат: {callback.data}")
            await callback.answer("Ошибка формата")
            return
        
        uid = int(parts[0])
        q_idx = int(parts[1])
        ans_idx = int(parts[2])
        
        # Проверяем, что это тот же пользователь
        if uid != callback.from_user.id:
            print(f"Чужой пользователь: {uid} != {callback.from_user.id}")
            await callback.answer("Это не твоя игра!")
            return
            
    except Exception as e:
        print(f"Ошибка парсинга: {e}, data: {callback.data}")
        await callback.answer("Ошибка данных")
        return

    session = user_sessions.get(uid)
    
    # Проверяем сессию
    if not session:
        print(f"Сессия не найдена для {uid}")
        await callback.answer("Игра не найдена")
        return
    
    # Проверяем индекс вопроса
    if session['current'] != q_idx:
        print(f"Не тот вопрос: ожидался {session['current']}, получен {q_idx}")
        await callback.answer("Этот вопрос уже не актуален")
        return
    
    # Проверяем, что вопрос существует
    if q_idx >= len(session['questions']):
        print(f"Вопрос {q_idx} вне диапазона")
        await callback.answer("Ошибка вопроса")
        return

    q = session['questions'][q_idx]
    
    # Проверяем, что вариант ответа существует
    if ans_idx >= len(q['options']):
        print(f"Вариант {ans_idx} вне диапазона")
        await callback.answer("Ошибка варианта")
        return

    correct = (ans_idx == q['correct'])
    points = DIFFICULTY_POINTS.get(q.get('difficulty', 'medium'), 2)

    if correct:
        session['score'] += points
        await callback.answer("✅ Верно!")
        await callback.message.answer(
            f"✅ **Верно!** +{points}\n\n{q.get('explanation', 'Молодец!')}", 
            parse_mode="Markdown"
        )
    else:
        correct_answer = q['options'][q['correct']]
        await callback.answer("❌ Неверно")
        await callback.message.answer(
            f"❌ **Неверно**\n\nПравильный ответ: **{correct_answer}**\n\n{q.get('explanation', 'В следующий раз!')}", 
            parse_mode="Markdown"
        )

    # Переходим к следующему вопросу
    session['current'] += 1
    await callback.message.delete()
    
    # Отправляем следующий вопрос или завершаем игру
    if session['current'] < len(session['questions']):
        await send_single_question(uid)
    else:
        await finish_single_game(uid)

async def finish_single_game(uid):
    """Завершает игру и сохраняет результат"""
    session = user_sessions.pop(uid, None)
    if not session:
        return

    score = session['score']
    total = sum(DIFFICULTY_POINTS.get(q.get('difficulty', 'medium'), 2) for q in session['questions'])
    percentage = (score / total * 100) if total > 0 else 0

    await db.save_game({
        "telegram_id": uid,
        "topic": session['topic'],
        "difficulty": "all",
        "score": score,
        "max_score": total,
        "percentage": round(percentage, 1),
        "duration": 0,
        "answers": []
    })

    result = (
        f"🎉 **ИГРА ОКОНЧЕНА!**\n\n"
        f"⭐ Результат: {score} из {total}\n"
        f"📊 Точность: {percentage:.1f}%"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Ещё игру", callback_data="menu_single")],
        [InlineKeyboardButton(text="◀️ Меню", callback_data="menu_back")]
    ])
    
    await bot.send_message(uid, result, reply_markup=keyboard, parse_mode="Markdown")

# ============================================================
# PVP (оставил как было, но можно сократить для объема)
# ============================================================
@dp.callback_query(F.data == "pvp_find")
async def pvp_find(callback: types.CallbackQuery):
    uid = callback.from_user.id
    name = callback.from_user.first_name or f"Player{uid}"
    success, msg = pvp_queue.add_to_queue(uid, name, None)
    await callback.message.edit_text(msg, reply_markup=back_menu())
    await callback.answer()
    await asyncio.sleep(1)
    await try_match()

@dp.callback_query(F.data == "pvp_leave")
async def pvp_leave(callback: types.CallbackQuery):
    pvp_queue.remove_from_queue(callback.from_user.id)
    await callback.message.edit_text("❌ Ты покинул очередь", reply_markup=back_menu())
    await callback.answer()

@dp.callback_query(F.data == "pvp_my")
async def pvp_my(callback: types.CallbackQuery):
    stats = await db.get_pvp_stats(callback.from_user.id)
    if not stats or stats['total'] == 0:
        await callback.message.edit_text("⚔️ Нет боёв", reply_markup=back_menu())
    else:
        win_rate = (stats['wins'] / stats['total'] * 100) if stats['total'] > 0 else 0
        text = (
            f"⚔️ **PvP статистика**\n\n"
            f"Боёв: {stats['total']}\n"
            f"✅ Побед: {stats['wins']}\n"
            f"❌ Поражений: {stats['losses']}\n"
            f"🤝 Ничьих: {stats['draws']}\n"
            f"📈 Процент: {win_rate:.1f}%"
        )
        await callback.message.edit_text(text, reply_markup=back_menu(), parse_mode="Markdown")
    await callback.answer()

async def try_match():
    p1, p2 = pvp_queue.find_match()
    if not p1 or not p2:
        return
    
    topic_id = random.choice(["math", "tiktok", "music2026"])
    questions = await get_questions_for_game(topic_id, PVP_QUESTIONS, "all")
    
    if not questions or len(questions) < PVP_QUESTIONS:
        # Если не получили вопросы, возвращаем игроков в очередь
        pvp_queue.add_to_queue(p1['id'], p1['name'], None)
        pvp_queue.add_to_queue(p2['id'], p2['name'], None)
        return
    
    game_id = pvp_queue.create_game(p1, p2, questions)
    
    await bot.send_message(p1['id'], f"🎮 **Соперник найден!**", parse_mode="Markdown")
    await bot.send_message(p2['id'], f"🎮 **Соперник найден!**", parse_mode="Markdown")
    
    await asyncio.sleep(1)
    await send_pvp_question(p1['id'], game_id)
    await send_pvp_question(p2['id'], game_id)

async def send_pvp_question(user_id, game_id):
    game = pvp_queue.active_games.get(game_id)
    if not game:
        return
    
    player = game['players'][user_id]
    if player['finished']:
        return
    
    q_idx = player['current']
    if q_idx >= len(game['questions']):
        return
    
    q = game['questions'][q_idx]
    points = DIFFICULTY_POINTS.get(q.get('difficulty', 'medium'), 2)
    
    builder = InlineKeyboardBuilder()
    for i, opt in enumerate(q['options']):
        builder.button(text=opt[:20], callback_data=f"p{game_id}_{q_idx}_{i}")
    builder.adjust(2)
    
    try:
        await bot.send_message(
            user_id,
            f"❓ **Вопрос {q_idx+1}/{len(game['questions'])}**\n\n{q['question']}",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"PvP ошибка: {e}")

@dp.callback_query(lambda c: c.data and c.data.startswith("p"))
async def pvp_answer(callback: types.CallbackQuery):
    try:
        data = callback.data[1:]
        parts = data.split("_")
        if len(parts) != 3:
            await callback.answer("Ошибка")
            return
        
        game_id = parts[0]
        q_idx = int(parts[1])
        ans_idx = int(parts[2])
        
    except Exception as e:
        print(f"PvP парсинг: {e}")
        await callback.answer("Ошибка данных")
        return
    
    uid = callback.from_user.id
    game = pvp_queue.active_games.get(game_id)
    
    if not game:
        await callback.answer("Игра не найдена")
        return
    
    player = game['players'].get(uid)
    if not player or player['finished'] or player['current'] != q_idx:
        await callback.answer("Не твой ход")
        return
    
    q = game['questions'][q_idx]
    correct = (ans_idx == q['correct'])
    points = DIFFICULTY_POINTS.get(q.get('difficulty', 'medium'), 2)
    
    if correct:
        player['score'] += points
        await callback.answer("✅ Верно!")
        await callback.message.answer(f"✅ **Верно!** +{points}", parse_mode="Markdown")
    else:
        correct_answer = q['options'][q['correct']]
        await callback.answer("❌ Неверно")
        await callback.message.answer(f"❌ **Неверно!**\n\nПравильный ответ: **{correct_answer}**", parse_mode="Markdown")
    
    player['current'] += 1
    if player['current'] >= len(game['questions']):
        player['finished'] = True
    
    await callback.message.delete()
    
    other_id = [pid for pid in game['players'] if pid != uid][0]
    if game['players'][other_id]['finished'] and player['finished']:
        await finish_pvp_game(game_id)
    else:
        await send_pvp_question(uid, game_id)

async def finish_pvp_game(game_id):
    game = pvp_queue.active_games.get(game_id)
    if not game:
        return
    
    p1_id, p2_id = list(game['players'].keys())
    p1 = game['players'][p1_id]
    p2 = game['players'][p2_id]
    
    if p1['score'] > p2['score']:
        winner = p1_id
    elif p2['score'] > p1['score']:
        winner = p2_id
    else:
        winner = None
    
    await db.save_pvp_match({
        'match_id': game_id,
        'player1_id': p1_id,
        'player2_id': p2_id,
        'winner_id': winner,
        'player1_score': p1['score'],
        'player2_score': p2['score'],
        'player1_name': p1['name'],
        'player2_name': p2['name']
    })
    
    result = f"🏆 **БИТВА ОКОНЧЕНА**\n\n"
    result += f"{p1['name']}: {p1['score']}\n"
    result += f"{p2['name']}: {p2['score']}\n\n"
    
    if winner:
        winner_name = game['players'][winner]['name']
        result += f"🎉 Победитель: {winner_name}"
    else:
        result += "🤝 Ничья"
    
    await bot.send_message(p1_id, result, parse_mode="Markdown")
    await bot.send_message(p2_id, result, parse_mode="Markdown")
    
    pvp_queue.end_game(game_id)

@dp.callback_query(F.data == "menu_leaders")
async def leaders(callback: types.CallbackQuery):
    top = await db.get_top_players(10)
    if not top:
        await callback.message.edit_text("🏆 Пока нет данных", reply_markup=back_menu())
    else:
        text = "🏆 **ТОП-10**\n\n"
        for i, u in enumerate(top, 1):
            name = u.first_name or f"Игрок{i}"
            text += f"{i}. {name} — {u.total_score} очков\n"
        await callback.message.edit_text(text, reply_markup=back_menu(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "menu_stats")
async def stats(callback: types.CallbackQuery):
    user_data = await db.get_user_stats(callback.from_user.id)
    if not user_data:
        await callback.message.edit_text("📊 Нет данных", reply_markup=back_menu())
    else:
        u = user_data['user']
        text = (
            f"📊 **Твоя статистика**\n\n"
            f"⭐ Всего очков: {u.total_score}\n"
            f"🎮 Сыграно игр: {u.games_played}\n"
            f"🏆 Лучший результат: {u.best_score}\n"
            f"⚔️ PvP: {u.pvp_wins}/{u.pvp_losses}/{u.pvp_draws}"
        )
        await callback.message.edit_text(text, reply_markup=back_menu(), parse_mode="Markdown")
    await callback.answer()

# ============================================================
# ЗАПУСК
# ============================================================
async def main():
    await db.create_tables()
    print("✅ БОТ ЗАПУЩЕН")
    print(f"📚 Тем: {len(questions_by_topic)}")
    print("🌍 OpenTDB API активен")
    print("👥 PvP режим готов")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())

