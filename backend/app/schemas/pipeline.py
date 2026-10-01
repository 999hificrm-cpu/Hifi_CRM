from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class PipelineStageOut(BaseModel):
    id: str
    pipeline_id: str
    name: str
    code: str
    order_index: int
    color: Optional[str] = "#3b82f6"
    win_probability: Optional[Decimal] = Decimal("0.0")
    is_won: bool = False
    is_lost: bool = False

    class Config:
        from_attributes = True


class PipelineStageCreate(BaseModel):
    name: str
    code: str
    order_index: int
    color: Optional[str] = "#3b82f6"
    win_probability: Optional[Decimal] = Decimal("0.0")
    is_won: bool = False
    is_lost: bool = False


class PipelineStageUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    order_index: Optional[int] = None
    color: Optional[str] = None
    win_probability: Optional[Decimal] = None
    is_won: Optional[bool] = None
    is_lost: Optional[bool] = None


class PipelineOut(BaseModel):
    id: str
    organization_id: str
    name: str
    description: Optional[str] = None
    is_default: bool
    status: str
    stages: List[PipelineStageOut] = []
    created_at: datetime

    class Config:
        from_attributes = True


class PipelineCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_default: bool = False
    stages: Optional[List[PipelineStageCreate]] = None
