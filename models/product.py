from pydoc import describe
from unicodedata import category
from pydantic import BaseModel
from typing import Optional
from datetime import date as dt
from typing import List

class Products(BaseModel):
    id: Optional[str] = None
    title: str
    price: float
    description: str
    category: str
    sub_category: str
    
class ProductDetailCreate(BaseModel):
    detail: str

class ProductCreate(BaseModel):
    title: str
    price: float
    category: str
    sub_category: str
    details: List[str]

class ProductDetail(BaseModel):
    id: int
    detail: str

    class Config:
        orm_mode = True

class Product(BaseModel):
    id: str
    title: str
    price: float
    category: str
    sub_category: str
    details: List[ProductDetail] = []

    class Config:
        orm_mode = True