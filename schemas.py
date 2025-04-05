from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

# Enum for pizza sizes
class PizzaSize(str, Enum):
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"

# Schema for creating a new pizza
class PizzaCreate(BaseModel):
    name: str = Field(..., example="Margherita")
    description: Optional[str] = Field(None, example="Classic cheese and tomato pizza")
    price: float = Field(..., example=9.99)
    size: PizzaSize = Field(..., example=PizzaSize.MEDIUM)
    availability: bool = Field(default=True)

# Schema for updating an existing pizza
class PizzaUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    size: Optional[PizzaSize] = None
    availability: Optional[bool] = None

# Schema for API response
class PizzaResponse(PizzaCreate):
    id: int

    class Config:
        orm_mode = True
