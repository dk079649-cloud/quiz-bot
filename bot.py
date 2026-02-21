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

# Импортируем нашу базу данных и PvP очередь
from database import db, pvp_queue

# ============================================================
# ТОКЕН БОТА
# ============================================================
TOKEN = "8242125476:AAFCzCQ6ngl8XiHL1Ax9C4cqylz23NJocus"

# ============================================================
# НАСТРОЙКИ
# ============================================================
QUESTIONS_PER_GAME = 10
PVP_QUESTIONS = 5  # В PvP режиме меньше вопросов
DIFFICULTY_POINTS = {
    "easy": 1,
    "medium": 2,
    "hard": 3,
    "expert": 5
}

# ============================================================
# ВОПРОСЫ (сократил для примера, но у тебя останутся все)
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
                "explanation": "Telegram запущен 14 августа 2013 года"
            },
            {
                "question": "Кто создал Telegram?",
                "options": ["Павел Дуров", "Илон Маск", "Марк Цукерберг", "Билл Гейтс"],
                "correct": 0,
                "difficulty": "easy",
                "explanation": "Павел Дуров — основатель Telegram"
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
                "explanation": "15 × 12 = 180"
            },
            {
                "question": "Чему равен квадратный корень из 144?",
                "options": ["10", "11", "12", "13"],
                "correct": 2,
                "difficulty": "easy",
                "explanation": "√144 = 12"
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
    builder.button(text="📚 Одиночная игра", callback_data="choose_topic")
    builder.button(text="🎲 Случайная тема", callback_data="random_topic")
    builder.button(text="👥 PvP Батл", callback_data="pvp_menu")
    builder.button(text="🏆 Таблица лидеров", callback_data="show_leaders")
    builder.button(text="📊 Моя статистика", callback_data="my_stats")
    builder.adjust(2)
    return builder.as_markup()

def get_pvp_keyboard():
    """Меню PvP режима"""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔍 Найти соперника", callback_data="pvp_find")
    builder.button(text="❌ Покинуть очередь", callback_data="pvp_leave")
    builder.button(text="🏆 Рейтинг PvP", callback_data="pvp_rating")
    builder.button(text="📊 Мои бои", callback_data="pvp_stats")
    builder.button(text="◀️ Назад", callback_data="back_to_menu")
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
# PvP ОБРАБОТЧИКИ
# ============================================================

@dp.callback_query(lambda c: c.data == "pvp_menu")
async def pvp_menu(callback: types.CallbackQuery):
    """Меню PvP режима"""
    await callback.message.edit_text(
        "👥 **PvP БАТЛ**\n\n"
        "Сражайся с другими игроками в реальном времени!\n\n"
        "📝 Правила:\n"
        f"• {PVP_QUESTIONS} вопросов\n"
        "• Кто больше наберет очков - тот победил\n"
        "• Ничья - если счет равный\n"
        "• Победа +50 рейтинга\n"
        "• Поражение -30 рейтинга\n"
        "• Ничья +10 рейтинга\n\n"
        "Выбери действие:",
        reply_markup=get_pvp_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "pvp_find")
async def pvp_find(callback: types.CallbackQuery):
    """Поиск соперника"""
    user_id = callback.from_user.id
    username = callback.from_user.first_name or f"Игрок_{user_id}"
    
    # Получаем пользователя из БД
    user = await db.get_or_create_user(
        telegram_id=user_id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name
    )
    
    # Добавляем в очередь
    success, message = pvp_queue.add_to_queue(user_id, username, user)
    
    if success:
        await callback.message.edit_text(
            f"{message}\n\n"
            "🔍 Ищем подходящего соперника...\n"
            "Как только найдется - я сообщу!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Отменить поиск", callback_data="pvp_leave")]
                ]
            )
        )
    else:
        await callback.answer(message, show_alert=True)
        return
    
    # Проверяем, не нашелся ли сразу соперник
    await check_pvp_match(callback.message.chat.id)
    await callback.answer()

@dp.callback_query(lambda c: c.data == "pvp_leave")
async def pvp_leave(callback: types.CallbackQuery):
    """Покинуть очередь"""
    user_id = callback.from_user.id
    pvp_queue.remove_from_queue(user_id)
    
    await callback.message.edit_text(
        "❌ Ты покинул очередь.\n"
        "Можешь попробовать снова позже!",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👥 PvP меню", callback_data="pvp_menu")],
                [InlineKeyboardButton(text="◀️ Главное меню", callback_data="back_to_menu")]
            ]
        )
    )
    await callback.answer()

async def check_pvp_match(chat_id):
    """Проверяет, есть ли пара в очереди"""
    player1, player2 = pvp_queue.find_match()
    
    if player1 and player2:
        # Создаем игру
        topic_id = random.choice(list(questions_by_topic.keys()))
        all_questions = questions_by_topic[topic_id]["questions"].copy()
        random.shuffle(all_questions)
        game_questions = all_questions[:PVP_QUESTIONS]
        
        game_id = pvp_queue.create_game(player1, player2, game_questions)
        
        # Отправляем уведомления обоим игрокам
        for player in [player1, player2]:
            await bot.send_message(
                player['id'],
                f"🎮 **СОПЕРНИК НАЙДЕН!**\n\n"
                f"Твой противник: **{player1['name'] if player['id'] == player2['id'] else player2['name']}**\n"
                f"📚 Тема: {questions_by_topic[topic_id]['name']}\n"
                f"📝 Вопросов: {PVP_QUESTIONS}\n\n"
                f"⚔️ Игра начинается!",
                parse_mode="Markdown"
            )
        
        # Отправляем первый вопрос первому игроку
        await send_pvp_question(player1['id'], game_id)

async def send_pvp_question(user_id, game_id):
    """Отправить PvP вопрос"""
    game = pvp_queue.active_games.get(game_id)
    if not game:
        return
    
    player = game['players'][user_id]
    q_num = player['current']
    
    if q_num >= game['total']:
        return
    
    q = game['questions'][q_num]
    points = DIFFICULTY_POINTS.get(q.get("difficulty", "medium"), 2)
    
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(q["options"]):
        builder.button(text=option, callback_data=f"pvp_{game_id}_{q_num}_{i}")
    builder.adjust(2)
    
    await bot.send_message(
        user_id,
        f"❓ **Вопрос {q_num + 1}/{game['total']}**\n\n"
        f"{q['question']}\n\n"
        f"⚡ Сложность: {q.get('difficulty', 'medium')} (+{points} баллов)",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data.startswith("pvp_"))
async def handle_pvp_answer(callback: types.CallbackQuery):
    """Обработка PvP ответа"""
    _, game_id, q_num, answer_idx = callback.data.split("_")
    q_num = int(q_num)
    answer_idx = int(answer_idx)
    
    user_id = callback.from_user.id
    game = pvp_queue.active_games.get(game_id)
    
    if not game:
        await callback.answer("Эта игра уже закончена!")
        return
    
    player = game['players'][user_id]
    
    if player['current'] != q_num:
        await callback.answer("Это не твой вопрос!")
        return
    
    q = game['questions'][q_num]
    correct = (answer_idx == q["correct"])
    points = DIFFICULTY_POINTS.get(q.get("difficulty", "medium"), 2)
    
    # Обрабатываем ответ
    result, status, winner = pvp_queue.submit_answer(
        user_id, q_num, answer_idx, correct, points
    )
    
    if correct:
        await callback.answer(f"✅ ПРАВИЛЬНО! +{points} баллов")
        await callback.message.answer(
            f"✨ **Верно!**\n\n+{points} баллов\n📚 {q['explanation']}"
        )
    else:
        correct_answer = q["options"][q["correct"]]
        await callback.answer("❌ Неправильно!")
        await callback.message.answer(
            f"❌ **Неправильно!**\n\n✅ Правильный ответ: **{correct_answer}**\n📚 {q['explanation']}"
        )
    
    await callback.message.delete()
    
    # Проверяем статус игры
    if status == "game_over":
        await end_pvp_game(game_id, winner)
    else:
        # Отправляем следующий вопрос
        await send_pvp_question(user_id, game_id)

async def end_pvp_game(game_id, winner_id):
    """Завершить PvP игру"""
    game = pvp_queue.active_games.get(game_id)
    if not game:
        return
    
    # Определяем результаты
    players = list(game['players'].items())
    p1_id, p1_data = players[0]
    p2_id, p2_data = players[1]
    
    if winner_id == p1_id:
        winner_name = p1_data['name']
        loser_name = p2_data['name']
        winner_score = p1_data['score']
        loser_score = p2_data['score']
        winner = p1_id
    elif winner_id == p2_id:
        winner_name = p2_data['name']
        loser_name = p1_data['name']
        winner_score = p2_data['score']
        loser_score = p1_data['score']
        winner = p2_id
    else:
        winner_name = "Ничья"
        loser_name = ""
        winner_score = p1_data['score']
        loser_score = p2_data['score']
        winner = None
    
    # Сохраняем результат в БД
    match_data = {
        'match_id': game_id,
        'player1_id': p1_id,
        'player2_id': p2_id,
        'winner_id': winner,
        'player1_score': p1_data['score'],
        'player2_score': p2_data['score'],
        'player1_name': p1_data['name'],
        'player2_name': p2_data['name']
    }
    await db.save_pvp_match(match_data)
    
    # Отправляем результаты обоим игрокам
    result_text = (
        f"🏆 **БИТВА ОКОНЧЕНА!** 🏆\n\n"
        f"📊 **Результаты:**\n"
        f"👤 {p1_data['name']}: {p1_data['score']} очков\n"
        f"👤 {p2_data['name']}: {p2_data['score']} очков\n\n"
    )
    
    if winner:
        result_text += f"🎉 **Победитель: {winner_name}!** 🎉"
    else:
        result_text += "🤝 **Ничья!**"
    
    for player_id in [p1_id, p2_id]:
        await bot.send_message(
            player_id,
            result_text,
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="👥 Еще битву", callback_data="pvp_find")],
                    [InlineKeyboardButton(text="◀️ Меню", callback_data="pvp_menu")]
                ]
            ),
            parse_mode="Markdown"
        )
    
    # Удаляем игру
    pvp_queue.end_game(game_id)

@dp.callback_query(lambda c: c.data == "pvp_rating")
async def pvp_rating(callback: types.CallbackQuery):
    """Показать PvP рейтинг"""
    # Тут будет выборка из БД топ игроков по PvP
    await callback.message.edit_text(
        "🏆 **PvP РЕЙТИНГ** 🏆\n\n"
        "⚡ Функция в разработке!\n"
        "Скоро здесь будет топ игроков по PvP боям.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="pvp_menu")]
            ]
        ),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "pvp_stats")
async def pvp_stats(callback: types.CallbackQuery):
    """Показать личную PvP статистику"""
    stats = await db.get_pvp_stats(callback.from_user.id)
    
    if stats and stats['total'] > 0:
        win_rate = (stats['wins'] / stats['total'] * 100) if stats['total'] > 0 else 0
        text = (
            f"📊 **ТВОЯ PvP СТАТИСТИКА**\n\n"
            f"⚔️ Всего боев: {stats['total']}\n"
            f"✅ Побед: {stats['wins']}\n"
            f"❌ Поражений: {stats['losses']}\n"
            f"🤝 Ничьих: {stats['draws']}\n"
            f"📈 Процент побед: {win_rate:.1f}%\n\n"
        )
        
        if stats['matches']:
            text += "📜 **Последние бои:**\n"
            for match in stats['matches'][:5]:
                if match.player1_id == callback.from_user.id:
                    opponent = match.player2_name
                    my_score = match.player1_score
                    opp_score = match.player2_score
                else:
                    opponent = match.player1_name
                    my_score = match.player2_score
                    opp_score = match.player1_score
                
                if match.winner_id == callback.from_user.id:
                    result = "✅ Победа"
                elif match.winner_id is None:
                    result = "🤝 Ничья"
                else:
                    result = "❌ Поражение"
                
                text += f"├ {result} vs {opponent} ({my_score}:{opp_score})\n"
    else:
        text = "📊 **У тебя пока нет PvP боёв**\n\nНайди соперника и сразись!"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="pvp_menu")]
            ]
        ),
        parse_mode="Markdown"
    )
    await callback.answer()

# ============================================================
# ОСТАЛЬНЫЕ ОБРАБОТЧИКИ (твои старые)
# ============================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Команда /start"""
    await db.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )
    
    welcome_text = (
        "🎯 **МЕГА-ВИКТОРИНА 2026**\n\n"
        f"📚 Всего тем: {len(questions_by_topic)}\n"
        "👥 Новый режим: PvP Батл!\n"
        "⚔️ Сражайся с другими игроками\n\n"
        "Выбери действие:"
    )
    await message.answer(welcome_text, reply_markup=get_main_keyboard(), parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "choose_topic")
async def choose_topic(callback: types.CallbackQuery):
    """Выбор темы"""
    await callback.message.edit_text(
        "📚 **Выбери тему:**",
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
    """Начало одиночной игры"""
    _, topic_id, difficulty = callback.data.split("_")
    
    all_questions = questions_by_topic[topic_id]["questions"].copy()
    
    if difficulty != "all":
        filtered = [q for q in all_questions if q.get("difficulty", "medium") == difficulty]
    else:
        filtered = all_questions
    
    if len(filtered) < QUESTIONS_PER_GAME:
        filtered = all_questions
    
    random.shuffle(filtered)
    game_questions = filtered[:QUESTIONS_PER_GAME]
    
    user_id = callback.from_user.id
    now = datetime.now()
    
    user_sessions[user_id] = {
        "score": 0,
        "question": 0,
        "name": callback.from_user.full_name or f"Игрок_{user_id}",
        "username": callback.from_user.username,
        "topic": topic_id,
        "topic_name": questions_by_topic[topic_id]["name"],
        "questions": game_questions,
        "total": len(game_questions),
        "difficulty": difficulty,
        "start_time": now.isoformat(),
        "answers": []
    }
    
    await callback.message.edit_text(
        f"🎮 **Одиночная игра начинается!**\n\n"
        f"📚 Тема: {questions_by_topic[topic_id]['name']}\n"
        f"📝 Вопросов: {len(game_questions)}",
        parse_mode="Markdown"
    )
    await asyncio.sleep(1)
    await send_single_question(callback.message, user_id)

async def send_single_question(message: types.Message, user_id: int):
    """Отправка вопроса в одиночной игре"""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    q_num = session["question"]
    questions = session["questions"]
    
    if q_num >= len(questions):
        await end_single_game(message, user_id)
        return
    
    q = questions[q_num]
    points = DIFFICULTY_POINTS.get(q.get("difficulty", "medium"), 2)
    
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(q["options"]):
        builder.button(text=option, callback_data=f"single_{q_num}_{i}")
    builder.adjust(2)
    
    await message.answer(
        f"❓ **Вопрос {q_num + 1}/{len(questions)}**\n\n"
        f"{q['question']}\n\n"
        f"⚡ Сложность: {q.get('difficulty', 'medium')} (+{points} баллов)",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data.startswith("single_"))
async def handle_single_answer(callback: types.CallbackQuery):
    """Обработка ответа в одиночной игре"""
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
            f"✨ **Верно!**\n\n+{points} баллов\n📚 {q['explanation']}"
        )
    else:
        correct_answer = q["options"][q["correct"]]
        await callback.answer("❌ Неправильно!")
        await callback.message.answer(
            f"❌ **Неправильно!**\n\n✅ Правильный ответ: **{correct_answer}**\n📚 {q['explanation']}"
        )
    
    session["question"] += 1
    await callback.message.delete()
    await send_single_question(callback.message, user_id)

async def end_single_game(message: types.Message, user_id: int):
    """Завершение одиночной игры"""
    session = user_sessions.get(user_id)
    if not session:
        return
    
    score = session["score"]
    total_possible = sum(DIFFICULTY_POINTS.get(q.get("difficulty", "medium"), 2) for q in session["questions"])
    percentage = (score / total_possible * 100) if total_possible > 0 else 0
    end_time = datetime.now()
    start_time = datetime.fromisoformat(session["start_time"])
    game_duration = (end_time - start_time).total_seconds() / 60
    
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
    
    result_text = (
        f"🎉 **ИГРА ОКОНЧЕНА!** 🎉\n\n"
        f"📚 Тема: {session['topic_name']}\n"
        f"⭐ Результат: **{score}** из {total_possible}\n"
        f"📊 Точность: **{percentage:.1f}%**\n"
        f"⏰ Время: {game_duration:.1f} минут\n\n"
    )
    
    if percentage >= 80:
        result_text += "🔥 **ФАНТАСТИКА!**"
    elif percentage >= 60:
        result_text += "👍 **ОТЛИЧНО!**"
    elif percentage >= 40:
        result_text += "👌 **ХОРОШО!**"
    else:
        result_text += "💪 **НЕПЛОХО!**"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📚 Другая тема", callback_data="choose_topic")],
            [InlineKeyboardButton(text="🏆 Таблица лидеров", callback_data="show_leaders")],
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
        name_display = user.username or user.first_name or f"Игрок_{user.telegram_id}"
        text += f"{medal} {name_display} — {user.total_score} очков (🎮 {user.games_played} игр)\n"
    
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
        text = "📊 **У тебя пока нет статистики**"
    else:
        user = stats['user']
        avg = user.total_score // user.games_played if user.games_played > 0 else 0
        
        text = (
            f"📊 **ТВОЯ СТАТИСТИКА** 📊\n\n"
            f"👤 Имя: {user.first_name or 'Не указано'}\n"
            f"⭐ Всего очков: {user.total_score}\n"
            f"🎮 Сыграно игр: {user.games_played}\n"
            f"📊 Средний результат: {avg}\n"
            f"🏆 Лучший результат: {user.best_score}\n\n"
            f"⚔️ PvP статистика:\n"
            f"├ Побед: {user.pvp_wins}\n"
            f"├ Поражений: {user.pvp_losses}\n"
            f"└ Ничьих: {user.pvp_draws}"
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
    await db.create_tables()
    print("🤖 ЗАПУСК МЕГА-ВИКТОРИНЫ")
    print(f"📚 Тем: {len(questions_by_topic)}")
    print("👥 PvP режим активирован")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
