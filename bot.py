import logging
import asyncio
import random
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
PVP_QUESTIONS = 5
DIFFICULTY_POINTS = {
    "easy": 1,
    "medium": 2,
    "hard": 3,
    "expert": 5
}

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Временные сессии для одиночной игры
user_sessions = {}

# ============================================================
# ПОЛНЫЙ СПИСОК ВОПРОСОВ (4 ТЕМЫ)
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
                "explanation": "Павел Дуров — создатель ВКонтакте и Telegram"
            },
            {
                "question": "Что означает 'MTProto' в Telegram?",
                "options": ["Название протокола", "Имя бота", "Тип стикера", "Вид шифрования"],
                "correct": 0,
                "difficulty": "hard",
                "explanation": "MTProto — собственный протокол шифрования Telegram"
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
            },
            {
                "question": "Сколько градусов в прямом угле?",
                "options": ["45°", "60°", "90°", "180°"],
                "correct": 2,
                "difficulty": "easy",
                "explanation": "Прямой угол равен 90 градусам"
            },
            {
                "question": "Чему равно число π?",
                "options": ["3.14", "3.16", "3.18", "3.12"],
                "correct": 0,
                "difficulty": "medium",
                "explanation": "π ≈ 3.14159"
            },
            {
                "question": "Сколько будет 25% от 200?",
                "options": ["25", "50", "75", "100"],
                "correct": 1,
                "difficulty": "easy",
                "explanation": "200 ÷ 4 = 50"
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
                "explanation": "Мировая популярность пришла в 2018"
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
                "explanation": "Duet позволяет записать видео рядом с другим"
            },
            {
                "question": "Какая самая популярная категория в TikTok?",
                "options": ["Танцы", "Юмор", "Еда", "Образование"],
                "correct": 0,
                "difficulty": "easy",
                "explanation": "Танцы — самая популярная категория"
            },
            {
                "question": "Кто самый популярный тиктокер?",
                "options": ["Charli D'Amelio", "Khaby Lame", "Bella Poarch", "Addison Rae"],
                "correct": 1,
                "difficulty": "hard",
                "explanation": "Khaby Lame — более 160 млн подписчиков"
            }
        ]
    },
    "music2026": {
        "name": "🎸 Музыка 2026",
        "emoji": "🎸",
        "icon": "🎤",
        "questions": [
            {
                "question": "Кто был самым прослушиваемым артистом 2025?",
                "options": ["Taylor Swift", "The Weeknd", "Bad Bunny", "Drake"],
                "correct": 0,
                "difficulty": "medium",
                "explanation": "Taylor Swift — артистка года"
            },
            {
                "question": "Какой жанр стал самым популярным в 2026?",
                "options": ["Поп", "Хип-хоп", "Электроника", "K-Pop"],
                "correct": 3,
                "difficulty": "hard",
                "explanation": "K-Pop продолжает захватывать мир"
            },
            {
                "question": "Какой фестиваль собрал больше всех в 2025?",
                "options": ["Coachella", "Tomorrowland", "Гластонбери", "Lollapalooza"],
                "correct": 1,
                "difficulty": "hard",
                "explanation": "Tomorrowland собрал 400 000 посетителей"
            },
            {
                "question": "Какая песня стала вирусной в 2025?",
                "options": ["Espresso", "We Can't Be Friends", "Beautiful Things", "Lose Control"],
                "correct": 0,
                "difficulty": "medium",
                "explanation": "Espresso Сабрины Карпентер"
            },
            {
                "question": "Кто выиграл Грэмми в 2026?",
                "options": ["Taylor Swift", "Billie Eilish", "Olivia Rodrigo", "SZA"],
                "correct": 0,
                "difficulty": "hard",
                "explanation": "Taylor Swift — альбом года"
            }
        ]
    }
}

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
        "🎯 **МЕГА-ВИКТОРИНА 2026**\n\n"
        f"📚 Всего тем: {len(questions_by_topic)}\n"
        f"📝 Всего вопросов: {sum(len(t['questions']) for t in questions_by_topic.values())}\n"
        "👥 PvP режим доступен\n"
        "✅ Работает на всех устройствах",
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

@dp.callback_query(F.data == "menu_pvp")
async def go_pvp(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👥 **PvP режим**\n\n"
        f"📝 {PVP_QUESTIONS} вопросов\n"
        "⚔️ Найди соперника и сразись!",
        reply_markup=pvp_menu(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "menu_leaders")
async def leaders(callback: types.CallbackQuery):
    top = await db.get_top_players(10)
    if not top:
        await callback.message.edit_text("🏆 Пока нет данных", reply_markup=back_menu())
    else:
        text = "🏆 **ТОП-10**\n\n"
        for i, u in enumerate(top, 1):
            name = u.first_name or f"Игрок{i}"
            text += f"{i}. {name} — {u.total_score} очков (🎮 {u.games_played})\n"
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
            f"⚔️ PvP: {u.pvp_wins} / {u.pvp_losses} / {u.pvp_draws}"
        )
        await callback.message.edit_text(text, reply_markup=back_menu(), parse_mode="Markdown")
    await callback.answer()

# ============================================================
# ОДИНОЧНАЯ ИГРА
# ============================================================
@dp.callback_query(F.data == "menu_single")
async def single_start(callback: types.CallbackQuery):
    uid = callback.from_user.id
    topic_id = random.choice(list(questions_by_topic.keys()))
    questions = random.sample(questions_by_topic[topic_id]["questions"], 5)

    user_sessions[uid] = {
        'score': 0,
        'current': 0,
        'questions': questions,
        'topic': topic_id,
        'start_time': datetime.now()
    }

    await callback.message.edit_text(
        f"🎮 **Одиночная игра**\n"
        f"Тема: {questions_by_topic[topic_id]['name']}\n"
        f"Вопросов: 5\n\n"
        f"Начинаем...",
        parse_mode="Markdown"
    )
    await callback.answer()
    await asyncio.sleep(1)
    await send_single_question(uid)

async def send_single_question(uid):
    session = user_sessions.get(uid)
    if not session:
        return

    q_idx = session['current']
    if q_idx >= len(session['questions']):
        await finish_single_game(uid)
        return

    q = session['questions'][q_idx]
    points = DIFFICULTY_POINTS.get(q.get('difficulty', 'medium'), 2)

    builder = InlineKeyboardBuilder()
    for i, opt in enumerate(q['options']):
        builder.button(text=opt, callback_data=f"single_{q_idx}_{i}")
    builder.adjust(2)

    await bot.send_message(
        uid,
        f"❓ **Вопрос {q_idx+1}/{len(session['questions'])}**\n\n{q['question']}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("single_"))
async def single_answer(callback: types.CallbackQuery):
    try:
        _, q_idx, ans_idx = callback.data.split("_")
        q_idx = int(q_idx)
        ans_idx = int(ans_idx)
    except:
        await callback.answer("Ошибка")
        return

    uid = callback.from_user.id
    session = user_sessions.get(uid)
    if not session or session['current'] != q_idx:
        await callback.answer("Уже не актуально")
        return

    q = session['questions'][q_idx]
    correct = (ans_idx == q['correct'])
    points = DIFFICULTY_POINTS.get(q.get('difficulty', 'medium'), 2)

    if correct:
        session['score'] += points
        await callback.answer(f"✅ Верно! +{points}")
        await callback.message.answer(f"✅ **Верно!** +{points}\n\n{q['explanation']}", parse_mode="Markdown")
    else:
        correct_answer = q['options'][q['correct']]
        await callback.answer("❌ Неверно")
        await callback.message.answer(f"❌ **Неверно**\n\nПравильный ответ: **{correct_answer}**\n\n{q['explanation']}", parse_mode="Markdown")

    session['current'] += 1
    await callback.message.delete()
    await send_single_question(uid)

async def finish_single_game(uid):
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
    await bot.send_message(uid, result, parse_mode="Markdown")

# ============================================================
# PVP - ИСПРАВЛЕННАЯ ВЕРСИЯ
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
            f"📈 Процент побед: {win_rate:.1f}%"
        )
        await callback.message.edit_text(text, reply_markup=back_menu(), parse_mode="Markdown")
    await callback.answer()

async def try_match():
    p1, p2 = pvp_queue.find_match()
    if not p1 or not p2:
        return

    topic_id = random.choice(list(questions_by_topic.keys()))
    questions = random.sample(questions_by_topic[topic_id]["questions"], PVP_QUESTIONS)
    game_id = pvp_queue.create_game(p1, p2, questions)

    topic_name = questions_by_topic[topic_id]['name']
    await bot.send_message(p1['id'], f"🎮 **Соперник найден!**\nТема: {topic_name}", parse_mode="Markdown")
    await bot.send_message(p2['id'], f"🎮 **Соперник найден!**\nТема: {topic_name}", parse_mode="Markdown")

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
        # КОРОТКИЙ ФОРМАТ - РАБОТАЕТ НА ВСЕХ УСТРОЙСТВАХ
        builder.button(text=opt, callback_data=f"pvp_{game_id}_{q_idx}_{i}")
    builder.adjust(2)

    try:
        await bot.send_message(
            user_id,
            f"❓ **Вопрос {q_idx+1}/{len(game['questions'])}**\n\n{q['question']}",
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Ошибка отправки PvP вопроса: {e}")

@dp.callback_query(lambda c: c.data and c.data.startswith("pvp_"))
async def pvp_answer(callback: types.CallbackQuery):
    try:
        # Разбираем короткий формат: pvp_GAMEID_QIDX_AIDX
        parts = callback.data.split("_")
        if len(parts) != 4:
            await callback.answer("Ошибка формата")
            return
            
        game_id = parts[1]
        q_idx = int(parts[2])
        ans_idx = int(parts[3])
        
    except Exception as e:
        print(f"Ошибка парсинга PvP: {e}")
        await callback.answer("Ошибка данных")
        return

    uid = callback.from_user.id
    game = pvp_queue.active_games.get(game_id)
    
    if not game:
        await callback.answer("Игра не найдена")
        return

    player = game['players'].get(uid)
    if not player:
        await callback.answer("Ты не в этой игре")
        return

    if player['finished']:
        await callback.answer("Игра уже закончена")
        return

    if player['current'] != q_idx:
        await callback.answer("Не твой вопрос")
        return

    q = game['questions'][q_idx]
    correct = (ans_idx == q['correct'])
    points = DIFFICULTY_POINTS.get(q.get('difficulty', 'medium'), 2)

    if correct:
        player['score'] += points
        await callback.answer("✅ Верно!")
        await callback.message.answer(f"✅ **Верно!** +{points} очков\n\n{q['explanation']}", parse_mode="Markdown")
    else:
        correct_answer = q['options'][q['correct']]
        await callback.answer("❌ Неверно")
        await callback.message.answer(f"❌ **Неверно!**\n\nПравильный ответ: **{correct_answer}**\n\n{q['explanation']}", parse_mode="Markdown")

    player['current'] += 1
    
    if player['current'] >= len(game['questions']):
        player['finished'] = True

    await callback.message.delete()

    # Проверяем, закончили ли оба
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
    result += f"{p1['name']}: {p1['score']} очков\n"
    result += f"{p2['name']}: {p2['score']} очков\n\n"
    if winner:
        winner_name = game['players'][winner]['name']
        result += f"🎉 Победитель: {winner_name}"
    else:
        result += "🤝 Ничья"

    await bot.send_message(p1_id, result, parse_mode="Markdown")
    await bot.send_message(p2_id, result, parse_mode="Markdown")

    pvp_queue.end_game(game_id)

# ============================================================
# ЗАПУСК
# ============================================================
async def main():
    await db.create_tables()
    print("✅ БОТ ЗАПУЩЕН")
    print(f"📚 Тем: {len(questions_by_topic)}")
    print(f"📝 Всего вопросов: {sum(len(t['questions']) for t in questions_by_topic.values())}")
    print("👥 PvP режим активен (исправлен)")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
