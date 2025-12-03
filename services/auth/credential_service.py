import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import Credential
from database.sqlite_db import get_db_session

class CredentialService:
    def __init__(self):
        pass

    async def store_credential(
        self, 
        db: AsyncSession, 
        user_id: str, 
        service_name: str, 
        credential_data: Dict[str, Any],
        expires_in: Optional[int] = None
    ) -> Credential:
        """Store a new credential (unencrypted for now)."""
        # Plain JSON dump
        encrypted_data = json.dumps(credential_data)
        
        expires_at = None
        if expires_in:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        credential = Credential(
            user_id=user_id,
            service_name=service_name,
            credential_data=None, 
            encrypted_token=encrypted_data, # Storing plain text here for now
            expires_at=expires_at
        )
        
        db.add(credential)
        await db.commit()
        await db.refresh(credential)
        return credential

    async def get_credential(
        self, 
        db: AsyncSession, 
        user_id: str, 
        service_name: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve credential."""
        query = select(Credential).where(
            Credential.user_id == user_id,
            Credential.service_name == service_name
        )
        result = await db.execute(query)
        credential = result.scalar_one_or_none()
        
        if not credential:
            return None
            
        if credential.expires_at and credential.expires_at < datetime.utcnow():
            await self.delete_credential(db, user_id, service_name)
            return None
            
        # Return plain data
        return json.loads(credential.encrypted_token)

    async def delete_credential(
        self, 
        db: AsyncSession, 
        user_id: str, 
        service_name: str
    ) -> bool:
        """Delete a credential."""
        query = select(Credential).where(
            Credential.user_id == user_id,
            Credential.service_name == service_name
        )
        result = await db.execute(query)
        credential = result.scalar_one_or_none()
        
        if not credential:
            return False
            
        await db.delete(credential)
        await db.commit()
        return True

    async def refresh_token(
        self, 
        db: AsyncSession, 
        user_id: str, 
        service_name: str, 
        new_token_data: Dict[str, Any],
        expires_in: Optional[int] = None
    ) -> Optional[Credential]:
        """Refresh a credential."""
        await self.delete_credential(db, user_id, service_name)
        return await self.store_credential(db, user_id, service_name, new_token_data, expires_in)

    def _encrypt_data(self, data: str) -> str:
        return data

    def _decrypt_data(self, encrypted_data: str) -> str:
        return encrypted_data

# Global instance
credential_service = CredentialService()
