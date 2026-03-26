# Model & App Status Report

## ✅ App Status: WORKING & RELIABLE

### Quick Summary
- **Model Performance**: R² = 0.4533 (45% variance explained)
- **Prediction Accuracy**: MAE ± R1,304,153 (29% of mean price)
- **App Status**: Running on http://localhost:8501
- **Reliability**: Good for comparative analysis, moderate for exact pricing

---

## Model Performance

### Current Metrics
- **R² Score**: 0.4533 (improved from 0.23 baseline)
- **MAE**: R1,304,153 
- **RMSE**: R1,895,048
- **CV R² (log-space)**: 0.4932 ± 0.2350

### Training Data
- **Total Properties**: 685 unique listings
- **Price Range**: R290,000 - R15,850,000
- **Mean Price**: R4,525,176
- **Location Coverage**: Overstrand region (Hermanus, Kleinbaai, Bettys Bay, etc.)

### Features Used (17 total)
**Numeric (14)**:
- bedrooms, bathrooms, accommodates, parking_spaces, square_meters
- pool, garden, security, near_beach
- location_score, property_age
- description_length, num_photos, has_agency

**Categorical (3)** - One-hot encoded:
- suburb (49+ unique values)
- city (multiple coastal towns)
- property_type_id (8+ property types)

### Top Predictive Features
1. **num_photos** (11%) - More photos = higher prices
2. **description_length** (8.5%) - Detailed listings command premium
3. **bathrooms** (8.4%) - Strong price driver
4. **property_type_id_8** (6.6%) - Specific property type
5. **parking_spaces** (6.1%)
6. **bedrooms** (5.8%)
7. **accommodates** (5.6%)
8. **square_meters** (3.2%) - Improved with text extraction

---

## Improvements Made

### Session Journey
1. **Expanded Dataset**: 124 → 685 properties (+452%)
2. **Hyperparameter Tuning**: RandomizedSearchCV with 20-25 iterations
3. **Log-Target Transform**: Reduced heteroscedasticity
4. **Location Encoding**: Added suburb + city one-hot (major R² gain)
5. **Square Meter Extraction**: Regex parsing from descriptions
6. **Corrupt File Recovery**: Fixed 100 duplicate listings

### R² Progression
- Initial (124 samples): 0.45
- Large dataset baseline: 0.23
- After tuning: 0.28
- With log-target: 0.27
- **With location encoding**: 0.45 ✓
- **With square_meters extraction**: 0.4533 ✓

---

## App Functionality

### What It Does
1. **Property Valuation**: Predicts market value based on 17 features
2. **Over/Under Pricing**: Compares asking price vs predicted value
3. **Market Comparison**: Shows position vs similar properties
4. **Visual Analytics**: Interactive charts with Plotly

### Inputs Required
- Basic: bedrooms, bathrooms, capacity, parking, size
- Amenities: pool, garden, security, pet-friendly, beach access
- Location: suburb, city, location score
- Marketing: description length, photo count, agency listing
- Property: type, age

### Outputs Provided
- Predicted market price (from log-transformed model)
- Price difference vs asking price
- Valuation status (undervalued/overvalued)
- Market percentile position
- Price distribution visualization
- Similar property comparison

---

## Reliability Assessment

### Strengths ✓
- **Location-aware**: Captures suburb/city premium effectively
- **Feature-rich**: 17 dimensions including marketing signals
- **Robust training**: 5-fold CV with diverse hyperparameter search
- **Log-target**: Stabilizes predictions across price ranges
- **Real data**: Trained on 685 actual Property24 listings

### Limitations ⚠️
- **R² = 0.45**: Explains 45% of variance; 55% due to unmeasured factors
- **MAE ±R1.3M**: Average prediction error is ~29% of mean price
- **High CV variance**: Performance varies across folds (location-dependent)
- **Missing features**: No photos quality, actual condition, views, renovations
- **Sample size**: 685 properties moderate for 17+ features after encoding
- **Geographic scope**: Overstrand region only; not generalizable

### When to Trust Predictions
✓ **Use for**:
- Comparative analysis between properties
- Identifying significantly over/underpriced listings
- Understanding feature importance in pricing
- Market trend analysis

⚠️ **Don't rely solely on**:
- Exact pricing (±R1.3M typical error)
- Properties far outside training data range
- Unique/luxury properties with rare features
- Final investment decisions (always consult professionals)

---

## Running the App

```bash
# Start the app
streamlit run app.py

# Access at
http://localhost:8501
```

### Test Prediction
A 3-bed, 2-bath Hermanus property (150 sqm, pool, garden, security, 30 photos):
- **Predicted**: R3,606,582
- **Range**: ±R1.3M (R2.3M - R4.9M realistic)

---

## Next Improvements (Optional)

### High Impact
- **GroupKFold by suburb**: Reduce location leakage in CV
- **XGBoost/CatBoost**: Better categorical + interaction handling
- **View/condition parsing**: Extract keywords from descriptions
- **Photo quality analysis**: Use image embeddings

### Medium Impact
- **Ensemble methods**: Stack RF + GB predictions
- **Target encoding**: Alternative to one-hot for high-cardinality suburbs
- **Outlier handling**: Winsorize instead of IQR removal
- **More data**: Scrape additional listings

### Low Priority
- **Feature interactions**: Manually engineer bedrooms*bathrooms, etc.
- **Seasonality**: Add listing date features
- **Agency effects**: Model agency reputation scores

---

## Model Files
- **Pipeline**: `models/airbnb_model.pkl` (includes preprocessing)
- **Metrics**: `models/metrics.json` (performance details)
- **Data**: `data/property24_data_full.csv` (685 properties)
- **Raw**: `raw_data/*.json` (22 files, 2182 total listings)

---

**Last Updated**: January 24, 2026
**Model Version**: v2.0 (location-aware with log-target)
