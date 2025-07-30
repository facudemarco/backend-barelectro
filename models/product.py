from pydoc import describe
from pydantic import BaseModel
from typing import Optional
from datetime import date as dt
        
class Products(BaseModel):
    id: Optional[str] = None
    title: str
    price: float
    description: str