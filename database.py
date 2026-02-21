from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, JSON, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.future import select
from datetime import datetime
import json
import os

# Создаем базовый класс для моделей
Base = declarative_base()

# Модель пользователя
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    registered_at = Column(DateTime, default=datetime.now)
    last_activity = Column(DateTime, default=datetime.now)
    
    # Статистика
    total_score = Column(Integer, default=0)
    games_played = Column(Integer, default=0)
    total_time = Column(Float, default=0.0)  # в минутах
    best_score = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"

# Модель игры
class Game(Base):
    __tablename__ = 'games'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)  # связь с User.id
    telegram_id = Column(BigInteger, nullable=False)
    
    # Данные игры
    topic = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    score = Column(Integer, default=0)
    max_score = Column(Integer, default=0)
    percentage = Column(Float, default=0.0)
    duration = Column(Float, default=0.0)  # в минутах
    
    # Время
    played_at = Column(DateTime, default=datetime.now)
    
    # Детали (сохраняем как JSON)
    answers = Column(String, default='[]')  # JSON строка с ответами
    
    def __repr__(self):
        return f"<Game(user_id={self.user_id}, score={self.score}/{self.max_score})>"

# Класс для работы с БД
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
            # Ищем пользователя
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
        """Сохраняет игру в БД"""
        async with self.async_session() as session:
            # Сначала получаем пользователя
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
    
    async def get_user_history(self, telegram_id, limit=20):
        """Возвращает историю игр пользователя"""
        async with self.async_session() as session:
            result = await session.execute(
                select(Game).where(Game.telegram_id == telegram_id)
                .order_by(Game.played_at.desc())
                .limit(limit)
            )
            return result.scalars().all()

# Создаем глобальный экземпляр БД
db = Database()