# Recipe Nutrients Calculator

New functionality for calculating recipe nutrients with an interactive UI.

## What was implemented

### Backend

1. **Schemas (backend/app/schemas/recipe.py)**:
   - `RecipeIngredient` - recipe ingredient
   - `RecipeNutrients` - recipe nutrients
   - `RecipeFulfillment` - recipe fulfillment status
   - `MissingNutrients` - products with missing nutrient data
   - `RecipeCalculateRequest/Response` - request/response for calculation
   - `RecipeConsumeRequest/Response` - request/response for consumption

2. **Service (backend/app/services/recipe.py)**:
   - `calculate_recipe_nutrients()` - main nutrient calculation function
   - `consume_recipe()` - recipe consumption function
   - `_process_recipe()` - process a single recipe (including nested recipes)
   - `_increase_nutrients_from_product()` - add product nutrients

3. **API Endpoints (backend/app/api/endpoints/recipes.py)**:
   - `POST /api/recipes/calculate` - calculate recipe nutrients
   - `POST /api/recipes/consume` - consume a recipe

### Frontend

1. **View (frontend/src/views/RecipeNutrientsView.vue)**:
   - Step-by-step interactive UI
   - Recipe ID input
   - Ingredients display
   - Total nutrients display
   - Per-serving nutrients display (if available)
   - Recipe fulfillment status
   - List of products with missing data
   - Consume recipe button (if all products are in stock)

2. **Routing**:
   - Added `/recipe-nutrients` route
   - Added navigation link

## Functionality

### Nutrient Calculation

#### Step 1: Enter Recipe ID
1. User enters a recipe ID
2. System fetches recipe data from Grocy

#### Step 2: Confirm portion changes (only if recipe has an associated product)
- If the recipe has an associated product, the system asks:
  - **"Did you change recipe portion measurements?"**
  - **If "Yes"** - calculation continues
  - **If "No"** - a message is shown asking to update portions in Grocy first

#### Step 3: Display results
3. The system:
   - Calculates nutrients from all ingredients
   - Handles nested recipes
   - Converts units of measurement (gram/ml/portion)
   - Calculates per-serving nutrients (if the recipe has a product_id)
   - Checks fulfillment status (whether all products are in stock)
   - Displays a list of products with missing nutrient data

### Recipe Consumption

#### Step 4: Consume (only if all products are available)
1. If all products are in stock, a "Consume Recipe" button is shown
2. After confirmation:
   - The recipe is consumed in Grocy
   - Stock levels are updated
   - A success message is displayed

## Usage Examples

### Recipe without an associated product
- Only total nutrients are displayed
- Consumption is unavailable
- Message: "Recipe has no associated product"

### Recipe with insufficient products
- Number of missing products is displayed
- Cost is shown
- Consumption is unavailable
- Message: "Missing X products. Cannot consume recipe"

### Recipe with all products available
- Total and per-serving nutrients are displayed
- Consumption is available
- Message: "Recipe can be consumed!"

## Technical Details

### Unit Conversion

The system supports automatic conversion between:
- Grams (ID: 82)
- Milliliters (ID: 85)
- Portions (ID: 103)

### Local Database Usage

The system uses a local database for:
- Storing product information
- Retrieving product names (instead of repeated Grocy API calls)

### Based on the original script

The nutrient calculation logic is based on the original Python script `recipe_nutrients.py` and fully replicates its functionality.

## Future Improvements

- [ ] Ability to update recipe product nutrients
- [ ] Export results to PDF/CSV
- [ ] Compare nutrients across different recipes
- [ ] Nutrient visualization (charts, diagrams)
- [ ] Batch processing support (multiple recipes at once)
