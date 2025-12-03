import uuid
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database.models import Artifact
from database.sqlite_db import get_db_session


class ArtifactService:
    def __init__(self):
        pass

    async def create_artifact(
        self,
        db: AsyncSession,
        session_id: str,
        artifact_id: str,
        filename: str,
        file_path: str,
        file_size: Optional[int] = None,
        content_type: Optional[str] = None
    ) -> Artifact:
        """Create a new artifact record."""
        artifact = Artifact(
            session_id=session_id,
            artifact_id=artifact_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
            content_type=content_type
        )
        
        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)
        return artifact

    async def get_artifact(
        self,
        db: AsyncSession,
        artifact_id: str
    ) -> Optional[Artifact]:
        """Retrieve an artifact by its unique artifact_id."""
        query = select(Artifact).where(Artifact.artifact_id == artifact_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def get_artifacts_for_session(
        self,
        db: AsyncSession,
        session_id: str
    ) -> List[Artifact]:
        """Get all artifacts associated with a session."""
        query = select(Artifact).where(Artifact.session_id == session_id)
        result = await db.execute(query)
        return result.scalars().all()

    async def delete_artifact(
        self,
        db: AsyncSession,
        artifact_id: str
    ) -> bool:
        """Delete an artifact record."""
        query = select(Artifact).where(Artifact.artifact_id == artifact_id)
        result = await db.execute(query)
        artifact = result.scalar_one_or_none()
        
        if not artifact:
            return False
            
        await db.delete(artifact)
        await db.commit()
        return True


# Global instance
artifact_service = ArtifactService()
