import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import User, Session

class SessionService:
    def __init__(self):
        pass

    async def get_user_by_telegram_id(self, db: AsyncSession, telegram_id: int) -> Optional[User]:
        query = select(User).where(User.telegram_id == telegram_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create_user(self, db: AsyncSession, telegram_id: int, username: Optional[str] = None) -> User:
        user = User(telegram_id=telegram_id, username=username)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

    async def get_or_create_user(self, db: AsyncSession, telegram_id: int, username: Optional[str] = None) -> User:
        user = await self.get_user_by_telegram_id(db, telegram_id)
        if not user:
            user = await self.create_user(db, telegram_id, username)
        elif username and user.username != username:
             # Update username if changed
             user.username = username
             await db.commit()
             await db.refresh(user)
        return user

    async def create_session(
        self, 
        db: AsyncSession, 
        user_id: str, 
        agent_name: str, 
        session_id: str
    ) -> Session:
        session = Session(
            user_id=user_id,
            agent_name=agent_name,
            session_id=session_id,
            session_data={}
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def get_session(self, db: AsyncSession, session_id: str) -> Optional[Session]:
        query = select(Session).where(Session.session_id == session_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_session_state(self, db: AsyncSession, session_id: str, new_state: dict) -> None:
        session = await self.get_session(db, session_id)
        if session:
            session.session_data = new_state
            await db.commit()

# Global instance
session_service = SessionService()
