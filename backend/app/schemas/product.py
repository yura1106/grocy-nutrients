from typing import Optional, Dict, Any
from pydantic import BaseModel, field_validator


class GrocyProductUserfields(BaseModel):
    """
    Schema for parsing Grocy product userfields (nutritional data)
    """
    nutrients_carbohydrates: Optional[str] = None
    nutrients_carbohydrates_of_sugars: Optional[str] = None
    nutrients_proteins: Optional[str] = None
    nutrients_fats: Optional[str] = None
    nutrients_fats_saturated: Optional[str] = None
    nutrients_salt: Optional[str] = None
    nutrients_fibers: Optional[str] = None

    @field_validator('*', mode='before')
    @classmethod
    def convert_to_string(cls, v):
        """Convert any value to string or None"""
        if v is None or v == "":
            return None
        return str(v)


class GrocyProductResponse(BaseModel):
    """
    Schema for parsing single product from Grocy API response
    """
    id: int
    name: str
    product_group_id: int
    active: int  # Grocy returns 0 or 1
    qu_id_stock: Optional[int] = None  # Quantity unit ID for stock
    calories: Optional[float] = None  # Calories from main product response
    userfields: Optional[Dict[str, Any]] = None

    def get_userfields(self) -> GrocyProductUserfields:
        """Parse userfields into typed schema"""
        if not self.userfields:
            return GrocyProductUserfields()
        return GrocyProductUserfields(**self.userfields)

    def is_active(self) -> bool:
        """Convert active field to boolean"""
        return bool(self.active)


class ProductNutrients(BaseModel):
    """
    Schema for storing parsed and converted nutritional data
    """
    calories: Optional[float] = None
    carbohydrates: Optional[float] = None
    carbohydrates_of_sugars: Optional[float] = None
    proteins: Optional[float] = None
    fats: Optional[float] = None
    fats_saturated: Optional[float] = None
    salt: Optional[float] = None
    fibers: Optional[float] = None

    @staticmethod
    def process_calories(calories: Optional[float], grocy_api: Any = None) -> Optional[float]:
        """
        Process/transform calories value before storing.

        Override this method to add custom numerical transformations.
        For example: unit conversion, rounding, API calls, etc.

        Args:
            calories: Raw calories value from Grocy
            grocy_api: GrocyAPI instance for making additional API calls if needed

        Returns:
            Processed calories value

        Example with grocy_api:
            # Get additional product info
            # product_details = grocy_api.get("/objects/products/123")
            # Apply custom logic based on product data
        """
        if calories is None:
            return None

        # Add your custom transformations here
        # Example: Convert kcal to kJ: return calories * 4.184
        # Example: Round to 2 decimals: return round(calories, 2)

        # Example with grocy_api (if needed):
        # if grocy_api:
        #     system_info = grocy_api.get("/system/info")
        #     # Use system_info for conversions

        return calories

    @staticmethod
    def from_grocy_product(
        grocy_product: "GrocyProductResponse",
        userfields: GrocyProductUserfields,
        grocy_api: Any = None
    ) -> "ProductNutrients":
        """
        Convert Grocy product and userfields to float values

        Args:
            grocy_product: Parsed Grocy product response
            userfields: Parsed userfields
            grocy_api: Optional GrocyAPI instance for additional transformations
        """
        def safe_float(value: Optional[str]) -> Optional[float]:
            if value is None or value == "":
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        return ProductNutrients(
            calories=ProductNutrients.process_calories(grocy_product.calories, grocy_api),
            carbohydrates=safe_float(userfields.nutrients_carbohydrates),
            carbohydrates_of_sugars=safe_float(userfields.nutrients_carbohydrates_of_sugars),
            proteins=safe_float(userfields.nutrients_proteins),
            fats=safe_float(userfields.nutrients_fats),
            fats_saturated=safe_float(userfields.nutrients_fats_saturated),
            salt=safe_float(userfields.nutrients_salt),
            fibers=safe_float(userfields.nutrients_fibers),
        )

    def has_changes(self, other: "ProductNutrients") -> bool:
        """Check if any nutrient value differs from another ProductNutrients"""
        return (
            self.calories != other.calories or
            self.carbohydrates != other.carbohydrates or
            self.carbohydrates_of_sugars != other.carbohydrates_of_sugars or
            self.proteins != other.proteins or
            self.fats != other.fats or
            self.fats_saturated != other.fats_saturated or
            self.salt != other.salt or
            self.fibers != other.fibers
        )


class ProductWithData(BaseModel):
    """
    Schema for product with latest nutritional data
    """
    # From Product table
    id: int
    grocy_id: int
    name: str
    active: bool
    product_group_id: int
    created_at: str

    # From latest ProductData
    price: Optional[float] = None
    calories: Optional[float] = None
    carbohydrates: Optional[float] = None
    carbohydrates_of_sugars: Optional[float] = None
    proteins: Optional[float] = None
    fats: Optional[float] = None
    fats_saturated: Optional[float] = None
    salt: Optional[float] = None
    fibers: Optional[float] = None
    data_created_at: Optional[str] = None


class ProductsListResponse(BaseModel):
    """
    Response schema for paginated products list
    """
    products: list[ProductWithData]
    total: int
    skip: int
    limit: int


class SyncResponse(BaseModel):
    """
    Response schema for sync endpoint
    """
    status: str
    processed: int
    updated: int
    new_history_records: int


class ProductSyncData(BaseModel):
    """
    Schema for product data in sync response
    """
    # Product info
    id: int
    grocy_id: int
    name: str
    active: bool
    product_group_id: int
    qu_id_stock: Optional[int] = None
    created_at: str

    # Latest nutritional data
    latest_data: Optional[Dict[str, Any]] = None


class SingleProductSyncResponse(BaseModel):
    """
    Response schema for single product sync endpoint with detailed data
    """
    status: str
    processed: int
    updated: int
    new_history_records: int

    # Data from Grocy API
    grocy_data: Dict[str, Any]

    # Data from local database after sync
    local_data: ProductSyncData


class ConsumeRequest(BaseModel):
    """
    Request schema for consume endpoint
    """
    date: str  # Format: YYYY-MM-DD


class ConsumeResponse(BaseModel):
    """
    Response schema for consume endpoint - stub for custom JSON from Grocy
    """
    status: str
    date: str
    data: Dict[str, Any]  # Custom JSON data from Grocy processing
