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

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    registered_at = Column(DateTime, default=datetime.now)
    last_activity = Column(DateTime, default=datetime.now)
    
    total_score = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    total_time = Column(Float, default=0.0)
    best_score = Column(Integer, default=0)
    
    pvp_wins = Column(Integer, default=0)
    pvp_losses = Column(Integer, default=0)
    pvp_draws = Column(Integer, default=0)

class Game(Base):
    __tablename__ = 'games'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    telegram_id = Column(BigInteger, nullable=False)
    topic = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    score = Column(Integer, default=0)
    max_score = Column(Integer, default=0)
    percentage = Column(Float, default=0.0)
    duration = Column(Float, default=0.0)
    played_at = Column(DateTime, default=datetime.now)
    answers = Column(String, default='[]')

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

class Database:
    def __init__(self, db_path='sqlite+aiosqlite:///quiz_bot.db'):
        self.engine = create_async_engine(db_path, echo=False)
        self.async_session = sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
    
    async def create_tables(self):
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Таблицы созданы")
    
    async def get_or_create_user(self, telegram_id, username=None, first_name=None, last_name=None):
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
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
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == game_data['telegram_id'])
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
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
            
            user.total_score += game_data['score']
            user.games_played += 1
            user.total_time += game_data['duration']
            if game_data['score'] > user.best_score:
                user.best_score = game_data['score']
            user.last_activity = datetime.now()
            
            await session.commit()
            return game
    
    async def get_top_players(self, limit=15):
        async with self.async_session() as session:
            result = await session.execute(
                select(User).order_by(User.total_score.desc()).limit(limit)
            )
            return result.scalars().all()
    
    async def get_user_stats(self, telegram_id):
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            result = await session.execute(
                select(Game).where(Game.user_id == user.id).order_by(Game.played_at.desc()).limit(10)
            )
            games = result.scalars().all()
            
            return {'user': user, 'games': games}
    
    async def save_pvp_match(self, match_data):
        async with self.async_session() as session:
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
    
    async def get_pvp_stats(self, telegram_id):
        async with self.async_session() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
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

db = Database()

# ============================================================
# PVP QUEUE - ИСПРАВЛЕННАЯ ВЕРСИЯ
# ============================================================

class PvPQueue:
    def __init__(self):
        self.queue = []
        self.active_games = {}
        self.user_game = {}
    
    def add_to_queue(self, user_id, username, user_data):
        if any(u['id'] == user_id for u in self.queue):
            return False, "❌ Ты уже в очереди!"
        
        if user_id in self.user_game:
            return False, "❌ Ты уже в игре!"
        
        self.queue.append({
            'id': user_id,
            'name': username,
            'data': user_data,
            'time': datetime.now()
        })
        return True, "✅ Ты в очереди. Ищем соперника..."
    
    def remove_from_queue(self, user_id):
        self.queue = [u for u in self.queue if u['id'] != user_id]
    
    def find_match(self):
        if len(self.queue) >= 2:
            player1 = self.queue.pop(0)
            player2 = self.queue.pop(0)
            return player1, player2
        return None, None
    
    def create_game(self, player1, player2, questions):
        # КОРОТКИЙ ID - ЭТО ВАЖНО!
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
        game_id = self.user_game.get(user_id)
        if game_id:
            return self.active_games.get(game_id)
        return None
    
    def submit_answer(self, user_id, question_idx, answer_idx, correct, points):
        game = self.get_game(user_id)
        if not game:
            return None, "Игра не найдена"
        
        player = game['players'][user_id]
        
        if player['current'] != question_idx:
            return None, "Не тот вопрос"
        
        player['answers'].append({
            'question': question_idx,
            'answer': answer_idx,
            'correct': correct
        })
        
        if correct:
            player['score'] += points
        
        player['current'] += 1
        
        if player['current'] >= game['total']:
            player['finished'] = True
            
            other_id = [pid for pid in game['players'].keys() if pid != user_id][0]
            if game['players'][other_id]['finished']:
                return game, "game_over", None
        
        return game, "continue", None
    
    def end_game(self, game_id):
        if game_id in self.active_games:
            game = self.active_games[game_id]
            for user_id in game['players']:
                if user_id in self.user_game:
                    del self.user_game[user_id]
            del self.active_games[game_id]
            return True
        return False

pvp_queue = PvPQueue()
