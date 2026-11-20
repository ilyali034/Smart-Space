from datetime import datetime, timezone 
from uuid import UUID, uuid4 
from pydantic import BaseModel, Field 

class Event(BaseModel): 
    event_id: UUID = Field(default_factory=uuid4) 
    correlaction_id: UUID | None = None 
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc)) 

    