from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime

class ProductServiceBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: Optional[str] = None
    type: Literal["PRODUCT", "SERVICE"] = "PRODUCT"
    description: Optional[str] = None
    price: Optional[float] = None
    currency: str = Field(default="INR", min_length=3, max_length=3)
    is_active: bool = True

class ProductServiceCreate(ProductServiceBase):
    pass

class ProductServiceUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    type: Optional[Literal["PRODUCT", "SERVICE"]] = None
    description: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None

class ProductServiceOut(ProductServiceBase):
    id: str
    organization_id: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
