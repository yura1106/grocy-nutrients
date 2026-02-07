"""
Schemas for consumption endpoints
"""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel


class ConsumptionCheckRequest(BaseModel):
    """Request schema for checking product availability"""
    date: str  # Format: YYYY-MM-DD


class ProductToBuy(BaseModel):
    """Schema for product that needs to be purchased"""
    product_id: int
    amount: float
    note: str


class ConsumptionCheckResponse(BaseModel):
    """Response schema for availability check"""
    status: str  # "success" or "insufficient_stock"
    products_to_consume: Dict[Any, Any]
    products_to_buy: Dict[Any, Any]
    message: str


class ShoppingListRequest(BaseModel):
    """Request schema for creating shopping list"""
    date: str
    products_to_buy: Dict[Any, Any]


class ShoppingListResponse(BaseModel):
    """Response schema for shopping list creation"""
    status: str
    message: str
    products_count: int


class DryRunRequest(BaseModel):
    """Request schema for dry run"""
    date: str


class ProductPreview(BaseModel):
    """Schema for product consumption preview"""
    grocy_id: int
    product_id: Optional[int]
    name: str
    quantity: float
    note: str
    calories: Optional[float] = None
    carbohydrates: Optional[float] = None
    carbohydrates_of_sugars: Optional[float] = None
    proteins: Optional[float] = None
    fats: Optional[float] = None
    fats_saturated: Optional[float] = None
    salt: Optional[float] = None
    fibers: Optional[float] = None


class DryRunResponse(BaseModel):
    """Response schema for dry run"""
    status: str
    date: str
    products: List[ProductPreview]
    total_calories: float
    total_nutrients: Dict[str, float]
    products_count: int


class ExecuteConsumptionRequest(BaseModel):
    """Request schema for executing consumption"""
    date: str


class ConsumedProductInfo(BaseModel):
    """Schema for consumed product info"""
    grocy_id: int
    name: str
    quantity: float
    note: str


class ExecuteConsumptionResponse(BaseModel):
    """Response schema for consumption execution"""
    status: str
    date: str
    consumed_products: List[ConsumedProductInfo]
    products_count: int
    message: str
