from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, JSON, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import json
import os
import random
import time

Base = declarative_base()

# ============================================================
# МОДЕЛИ БАЗЫ ДАННЫХ
# ============================================================

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    registered_at = Column(DateTime, default=datetime.now)
    last_activity = Column(DateTime, default=datetime.now)
    
    # Общая статистика
    total_score = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    total_time = Column(Float, default=0.0)
    best_score = Column(Integer, default=0)
    
    # PvP статистика
    pvp_wins = Column(Integer, default=0)
    pvp_losses = Column(Integer, default=0)
    pvp_draws = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"

class Game(Base):
    __tablename__ = 'games'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    telegram_id = Column(BigInteger, nullable=False)
    
    # Данные игры
    topic = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    score = Column(Integer, default=0)
    max_score = Column(Integer, default=0)
    percentage = Column(Float, default=0.0)
    duration = Column(Float, default=0.0)
    
    # Время
    played_at = Column(DateTime, default=datetime.now)
    
    # Детали
    answers = Column(String, default='[]')
    
    def __repr__(self):
        return f"<Game(user_id={self.user_id}, score={self.score}/{self.max_score})>"

class PvPMatch(Base):
    __tablename__ = 'pvp_matches'
    
    id = Column(Integer, primary_key=True)
    match_id = Column(String, unique=True, nullable=False)
    player1_id = Column(BigInteger, nullable=False)
    player2_id = Column(BigInteger, nullable=False)
    winner_id = Column(BigInteger, nullable=True)
    player1_score = Column(Integer, default=0)
    player2_score = Column(Integer, default=0)
    player1_name = Column(String)
    player2_name = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    finished_at = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<PvPMatch({self.player1_name} vs {self.player2_name})>"

# ============================================================
# КЛАСС ДЛЯ РАБОТЫ С БД
# ============================================================

class Database:
    def __init__(self, db_path='sqlite+aiosqlite:///quiz_bot.db'):
        self.engine = create_async_engine(db_path, echo=False)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
    
    async def create_tables(self):
        """Создает таблицы, если их нет"""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Таблицы базы данных созданы")
    
    async def get_or_create_user(self, telegram_id, username=None, first_name=None, last_name=None):
        """Получает пользователя или создает нового"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                # Обновляем активность
                user.last_activity = datetime.now()
                if username:
                    user.username = username
                if first_name:
                    user.first_name = first_name
                if last_name:
                    user.last_name = last_name
                await session.commit()
                return user
            else:
                # Создаем нового
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)
                await session.commit()
                return user
    
    async def save_game(self, game_data):
        """Сохраняет одиночную игру в БД"""
        async with self.async_session() as session:
            # Получаем пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == game_data['telegram_id'])
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Создаем запись игры
            game = Game(
                user_id=user.id,
                telegram_id=game_data['telegram_id'],
                topic=game_data['topic'],
                difficulty=game_data['difficulty'],
                score=game_data['score'],
                max_score=game_data['max_score'],
                percentage=game_data['percentage'],
                duration=game_data['duration'],
                answers=json.dumps(game_data.get('answers', []), ensure_ascii=False)
            )
            session.add(game)
            
            # Обновляем статистику пользователя
            user.total_score += game_data['score']
            user.games_played += 1
            user.total_time += game_data['duration']
            if game_data['score'] > user.best_score:
                user.best_score = game_data['score']
            user.last_activity = datetime.now()
            
            await session.commit()
            return game
    
    async def save_pvp_match(self, match_data):
        """Сохраняет PvP матч в БД"""
        async with self.async_session() as session:
            # Создаем запись матча
            match = PvPMatch(
                match_id=match_data['match_id'],
                player1_id=match_data['player1_id'],
                player2_id=match_data['player2_id'],
                winner_id=match_data.get('winner_id'),
                player1_score=match_data['player1_score'],
                player2_score=match_data['player2_score'],
                player1_name=match_data['player1_name'],
                player2_name=match_data['player2_name'],
                finished_at=datetime.now()
            )
            session.add(match)
            
            # Обновляем статистику игроков
            for player_id in [match_data['player1_id'], match_data['player2_id']]:
                result = await session.execute(
                    select(User).where(User.telegram_id == player_id)
                )
                user = result.scalar_one_or_none()
                if user:
                    if match_data.get('winner_id') == player_id:
                        user.pvp_wins += 1
                    elif match_data.get('winner_id') is None:
                        user.pvp_draws += 1
                    elif match_data.get('winner_id') != player_id:
                        user.pvp_losses += 1
            
            await session.commit()
            return match
    
    async def get_top_players(self, limit=15):
        """Возвращает топ игроков по общему счету"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).order_by(User.total_score.desc()).limit(limit)
            )
            return result.scalars().all()
    
    async def get_user_stats(self, telegram_id):
        """Возвращает подробную статистику пользователя"""
        async with self.async_session() as session:
            # Получаем пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Получаем последние игры
            result = await session.execute(
                select(Game).where(Game.user_id == user.id).order_by(Game.played_at.desc()).limit(10)
            )
            games = result.scalars().all()
            
            return {'user': user, 'games': games}
    
    async def get_pvp_stats(self, telegram_id):
        """Возвращает PvP статистику игрока"""
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            # Получаем последние матчи
            result = await session.execute(
                select(PvPMatch).where(
                    (PvPMatch.player1_id == telegram_id) | (PvPMatch.player2_id == telegram_id)
                ).order_by(PvPMatch.finished_at.desc()).limit(10)
            )
            matches = result.scalars().all()
            
            return {
                'wins': user.pvp_wins,
                'losses': user.pvp_losses,
                'draws': user.pvp_draws,
                'total': user.pvp_wins + user.pvp_losses + user.pvp_draws,
                'matches': matches
            }
    
    async def get_user_history(self, telegram_id, limit=20):
        """Возвращает историю игр пользователя"""
        async with self.async_session() as session:
            # Сначала получаем пользователя
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return []
            
            # Получаем игры
            result = await session.execute(
                select(Game).where(Game.user_id == user.id)
                .order_by(Game.played_at.desc())
                .limit(limit)
            )
            return result.scalars().all()

# ============================================================
# PVP QUEUE - УПРАВЛЕНИЕ ОЧЕРЕДЬЮ ИГРОКОВ
# ============================================================

class PvPQueue:
    def __init__(self):
        self.queue = []  # Очередь ожидания
        self.active_games = {}  # Активные игры {game_id: data}
        self.user_game = {}  # Связь пользователь -> игра {user_id: game_id}
    
    def add_to_queue(self, user_id, username, user_data):
        """Добавить игрока в очередь"""
        # Проверяем, не в очереди ли уже
        if any(u['id'] == user_id for u in self.queue):
            return False, "❌ Ты уже в очереди!"
        
        # Проверяем, не в игре ли уже
        if user_id in self.user_game:
            return False, "❌ Ты уже в игре!"
        
        # Добавляем в очередь
        self.queue.append({
            'id': user_id,
            'name': username,
            'data': user_data,
            'time': datetime.now()
        })
        return True, "✅ Ты в очереди. Ищем соперника..."
    
    def remove_from_queue(self, user_id):
        """Удалить игрока из очереди"""
        self.queue = [u for u in self.queue if u['id'] != user_id]
    
    def find_match(self):
        """Найти пару игроков"""
        if len(self.queue) >= 2:
            player1 = self.queue.pop(0)
            player2 = self.queue.pop(0)
            return player1, player2
        return None, None
    
    def create_game(self, player1, player2, questions):
        """Создать новую игру с коротким ID"""
        # Короткий ID для callback_data
        game_id = f"g{int(time.time())}{random.randint(100,999)}"
        
        game_data = {
            'id': game_id,
            'players': {
                player1['id']: {
                    'name': player1['name'],
                    'data': player1.get('data'),
                    'score': 0,
                    'current': 0,
                    'answers': [],
                    'finished': False
                },
                player2['id']: {
                    'name': player2['name'],
                    'data': player2.get('data'),
                    'score': 0,
                    'current': 0,
                    'answers': [],
                    'finished': False
                }
            },
            'questions': questions,
            'total': len(questions),
            'start_time': datetime.now().isoformat(),
            'status': 'active'
        }
        
        self.active_games[game_id] = game_data
        self.user_game[player1['id']] = game_id
        self.user_game[player2['id']] = game_id
        
        return game_id
    
    def get_game(self, user_id):
        """Получить игру пользователя"""
        game_id = self.user_game.get(user_id)
        if game_id:
            return self.active_games.get(game_id)
        return None
    
    def submit_answer(self, user_id, question_idx, answer_idx, correct, points):
        """Записать ответ игрока"""
        game = self.get_game(user_id)
        if not game:
            return None, "Игра не найдена"
        
        player = game['players'][user_id]
        
        # Проверяем, что это правильный вопрос
        if player['current'] != question_idx:
            return None, "Не тот вопрос"
        
        # Сохраняем ответ
        player['answers'].append({
            'question': question_idx,
            'answer': answer_idx,
            'correct': correct
        })
        
        if correct:
            player['score'] += points
        
        # Переходим к следующему вопросу
        player['current'] += 1
        
        # Проверяем, закончил ли игрок
        if player['current'] >= game['total']:
            player['finished'] = True
            
            # Проверяем, закончили ли оба
            other_id = [pid for pid in game['players'].keys() if pid != user_id][0]
            if game['players'][other_id]['finished']:
                # Игра окончена
                return game, "game_over"
        
        return game, "continue"
    
    def end_game(self, game_id):
        """Завершить игру и очистить данные"""
        if game_id in self.active_games:
            game = self.active_games[game_id]
            for user_id in game['players']:
                if user_id in self.user_game:
                    del self.user_game[user_id]
            del self.active_games[game_id]
            return True
        return False
    
    def get_queue_length(self):
        """Получить длину очереди"""
        return len(self.queue)
    
    def clear_queue(self):
        """Очистить очередь (для тестирования)"""
        self.queue = []

# ============================================================
# ГЛОБАЛЬНЫЕ ЭКЗЕМПЛЯРЫ
# ============================================================

db = Database()
pvp_queue = PvPQueue()
