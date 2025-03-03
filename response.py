
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field
import datetime


class ExtractionAnalyticsDto(BaseModel):
    tenantId: str
    query: str
    answer: str
    contents: List[str]
    totalDuration: int
    loadDuration: int
    promptEvalDuration: int
    evalDuration: int
    eventTime: int = Field(default_factory=lambda: int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000))



