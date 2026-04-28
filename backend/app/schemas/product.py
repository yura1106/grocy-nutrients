from typing import Any

from pydantic import BaseModel, field_validator

from app.services.grocy_api import GrocyAPI, GrocyError


class GrocyProductUserfields(BaseModel):
    """
    Schema for parsing Grocy product userfields (nutritional data)
    """

    nutrients_carbohydrates: str | None = None
    nutrients_carbohydrates_of_sugars: str | None = None
    nutrients_proteins: str | None = None
    nutrients_fats: str | None = None
    nutrients_fats_saturated: str | None = None
    nutrients_salt: str | None = None
    nutrients_fibers: str | None = None

    @field_validator("*", mode="before")
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
    qu_id_stock: int | None = None  # Quantity unit ID for stock
    calories: float | None = None  # Calories from main product response
    userfields: dict[str, Any] | None = None

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

    calories: float | None = None
    carbohydrates: float | None = None
    carbohydrates_of_sugars: float | None = None
    proteins: float | None = None
    fats: float | None = None
    fats_saturated: float | None = None
    salt: float | None = None
    fibers: float | None = None

    @staticmethod
    def process_calories(
        grocy_product: "GrocyProductResponse", grocy_api: GrocyAPI
    ) -> float | None:
        """
        Process/transform calories value before storing.

        Override this method to add custom numerical transformations.
        For example: unit conversion, rounding, API calls, etc.

        Args:
            calories: Raw calories value from Grocy
            grocy_api: GrocyAPI instance for making additional API calls if needed

        Returns:
            Processed calories value
        """
        if grocy_product.calories is None:
            return 0

        factor = 1
        if not grocy_api.is_gram_or_ml(grocy_product.qu_id_stock):
            try:
                factor = grocy_api.get_conversion_reverse_factor_safe(
                    grocy_product.id,
                    grocy_product.qu_id_stock,
                    grocy_api.gram_ml_units,
                )
            except GrocyError:
                return grocy_product.calories

        return round(grocy_product.calories * factor, 2)

    @staticmethod
    def from_grocy_product(
        grocy_product: "GrocyProductResponse",
        userfields: GrocyProductUserfields,
        grocy_api: GrocyAPI,
    ) -> "ProductNutrients":
        """
        Convert Grocy product and userfields to float values

        Args:
            grocy_product: Parsed Grocy product response
            userfields: Parsed userfields
            grocy_api: Optional GrocyAPI instance for additional transformations
        """

        def safe_float(value: str | None) -> float | None:
            if value is None or value == "":
                return None
            try:
                return float(value)
            except (ValueError, TypeError):
                return None

        return ProductNutrients(
            calories=ProductNutrients.process_calories(grocy_product, grocy_api),
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
            self.calories != other.calories
            or self.carbohydrates != other.carbohydrates
            or self.carbohydrates_of_sugars != other.carbohydrates_of_sugars
            or self.proteins != other.proteins
            or self.fats != other.fats
            or self.fats_saturated != other.fats_saturated
            or self.salt != other.salt
            or self.fibers != other.fibers
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
    calories: float | None = None
    carbohydrates: float | None = None
    carbohydrates_of_sugars: float | None = None
    proteins: float | None = None
    fats: float | None = None
    fats_saturated: float | None = None
    salt: float | None = None
    fibers: float | None = None
    data_created_at: str | None = None


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
    total: int | None = None
    has_more: bool = False


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
    qu_id_stock: int | None = None
    created_at: str

    # Latest nutritional data
    latest_data: dict[str, Any] | None = None


class SingleProductSyncResponse(BaseModel):
    """
    Response schema for single product sync endpoint with detailed data
    """

    status: str
    processed: int
    updated: int
    new_history_records: int

    # Data from Grocy API
    grocy_data: dict[str, Any]

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
    data: dict[str, Any]  # Custom JSON data from Grocy processing


class ProductHistoryItem(BaseModel):
    """Single product data history item"""

    id: int
    calories: float | None = None
    carbohydrates: float | None = None
    carbohydrates_of_sugars: float | None = None
    proteins: float | None = None
    fats: float | None = None
    fats_saturated: float | None = None
    salt: float | None = None
    fibers: float | None = None
    created_at: str


class ProductDetailResponse(BaseModel):
    """Response with product details and data history"""

    id: int
    grocy_id: int
    name: str
    active: bool
    product_group_id: int
    qu_id_stock: int | None = None
    created_at: str
    history: list[ProductHistoryItem]
    total_history: int
