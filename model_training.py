import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, RandomizedSearchCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import pickle
import os
import json
from datetime import datetime

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Try to load full data (with suburb/city) else feature-only, otherwise use sample data
data_file_full = os.path.join(script_dir, 'data/property24_data_full.csv')
data_file = os.path.join(script_dir, 'data/property24_data.csv')
using_sample = False
if os.path.exists(data_file_full):
    print("=" * 60)
    print("LOADING FULL PROPERTY24 DATA (with location)")
    print("=" * 60)
    df = pd.read_csv(data_file_full)
    print(f"✓ Loaded {len(df)} properties from Property24 (full)")
elif os.path.exists(data_file):
    print("=" * 60)
    print("LOADING REAL PROPERTY24 DATA")
    print("=" * 60)
    df = pd.read_csv(data_file)
    print(f"✓ Loaded {len(df)} real properties from Property24")
else:
    # Create sample data for Overstrand properties
    print("=" * 60)
    print("LOADING SAMPLE DATA (Real data not found)")
    print("=" * 60)
    np.random.seed(42)
    n_samples = 1000

    data = {
        'bedrooms': np.random.randint(1, 7, n_samples),
        'bathrooms': np.random.randint(1, 5, n_samples),
        'accommodates': np.random.randint(2, 11, n_samples),
        'parking_spaces': np.random.randint(0, 4, n_samples),
        'square_meters': np.random.uniform(50, 500, n_samples),
        'pool': np.random.choice([0, 1], n_samples, p=[0.6, 0.4]),
        'near_beach': np.random.choice([0, 1], n_samples, p=[0.3, 0.7]),  # More properties near beach in Overstrand
        'location_score': np.random.uniform(1, 10, n_samples),  # New feature
        'property_age': np.random.randint(0, 50, n_samples),  # New feature
        'price': np.random.uniform(1000000, 5000000, n_samples)  # In ZAR
    }

    # Make price somewhat realistic based on features
    df = pd.DataFrame(data)
    df['price'] = (
        df['bedrooms'] * 200000 +
        df['bathrooms'] * 150000 +
        df['accommodates'] * 100000 +
        df['parking_spaces'] * 50000 +
        df['square_meters'] * 1000 +
        df['pool'] * 300000 +
        df['near_beach'] * 500000 +  # Beach access is valuable
        df['location_score'] * 150000 +
        np.random.normal(0, 500000, n_samples)
    ).clip(500000, 10000000)

    # Features for model
    numeric_features = ['bedrooms', 'bathrooms', 'accommodates', 'parking_spaces', 'square_meters', 'pool', 'near_beach', 'location_score', 'property_age']
    categorical_features = []
    X = df[numeric_features]
    y = df['price']
    y_log = np.log(y)
    using_sample = True

if not using_sample:
    # Use numeric features and add categorical features for location
    numeric_features = ['bedrooms', 'bathrooms', 'accommodates', 'parking_spaces', 'square_meters', 
                        'pool', 'garden', 'security', 'near_beach', 'location_score', 
                        'property_age', 'description_length', 'num_photos', 'has_agency']
    categorical_features = ['suburb', 'city', 'property_type_id']
    # Only use features that exist in the dataframe
    numeric_features = [f for f in numeric_features if f in df.columns]
    categorical_features = [f for f in categorical_features if f in df.columns]
    y = df['price']
    X = df[numeric_features + categorical_features]
    y_log = np.log(y)
    print(f"Using {len(numeric_features)} numeric + {len(categorical_features)} categorical features: {numeric_features + categorical_features}")
    print(f"\nData Info:")
    print(f"  Price range: R{y.min():,.0f} - R{y.max():,.0f}")
    print(f"  Price mean: R{y.mean():,.0f}")

# Split data (use log-transformed target)
X_train, X_test, y_train_log, y_test_log = train_test_split(X, y_log, test_size=0.2, random_state=42)

# Preprocess: OneHotEncode categorical, pass through numeric (no scaling needed for trees)
preprocess = ColumnTransformer(
    transformers=[
        ('num', 'passthrough', numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
    ]
)

# Train RandomForest with optimized hyperparameters
print("=" * 60)
print("HYPERPARAMETER TUNING (RandomizedSearchCV)")
print("=" * 60)

# Random Forest tuning (with preprocessing pipeline)
rf_base = RandomForestRegressor(random_state=42, n_jobs=-1)
rf_pipeline = Pipeline(steps=[('preprocess', preprocess), ('model', rf_base)])
rf_param_distributions = {
    'model__n_estimators': [200, 400, 800],
    'model__max_depth': [None, 10, 15, 20, 30],
    'model__min_samples_split': [2, 5, 10],
    'model__min_samples_leaf': [1, 2, 4],
    'model__max_features': ['sqrt', 'log2', 0.5, 1.0],
    'model__bootstrap': [True, False]
}
rf_search = RandomizedSearchCV(
    rf_pipeline,
    rf_param_distributions,
    n_iter=20,
    cv=5,
    scoring='r2',
    n_jobs=-1,
    random_state=42,
    verbose=1
)
rf_search.fit(X_train, y_train_log)
rf_model = rf_search.best_estimator_
rf_best_params = rf_search.best_params_
print(f"✓ Random Forest best params: {rf_best_params}")

# Gradient Boosting tuning (with preprocessing pipeline)
gb_base = GradientBoostingRegressor(random_state=42)
gb_pipeline = Pipeline(steps=[('preprocess', preprocess), ('model', gb_base)])
gb_param_distributions = {
    'model__n_estimators': [100, 200, 300, 500],
    'model__learning_rate': [0.03, 0.05, 0.1, 0.2],
    'model__max_depth': [3, 4, 5, 6, 7],
    'model__min_samples_split': [2, 5, 10],
    'model__min_samples_leaf': [1, 2, 4],
    'model__subsample': [0.8, 1.0]
}
gb_search = RandomizedSearchCV(
    gb_pipeline,
    gb_param_distributions,
    n_iter=25,
    cv=5,
    scoring='r2',
    n_jobs=-1,
    random_state=42,
    verbose=1
)
gb_search.fit(X_train, y_train_log)
gb_model = gb_search.best_estimator_
gb_best_params = gb_search.best_params_
print(f"✓ Gradient Boosting best params: {gb_best_params}")

# Evaluate RandomForest
print("\n" + "=" * 60)
print("RANDOM FOREST MODEL EVALUATION")
print("=" * 60)
# Predict in log space, evaluate in price space
y_pred_rf_log = rf_model.predict(X_test)
y_pred_rf = np.exp(y_pred_rf_log)
y_test_price = np.exp(y_test_log)
mae_rf = mean_absolute_error(y_test_price, y_pred_rf)
rmse_rf = np.sqrt(mean_squared_error(y_test_price, y_pred_rf))
r2_rf = r2_score(y_test_price, y_pred_rf)

print(f"MAE (Mean Absolute Error): R{mae_rf:,.0f}")
print(f"RMSE (Root Mean Squared Error): R{rmse_rf:,.0f}")
print(f"R² Score: {r2_rf:.4f}")

# Cross-validation score for RandomForest (best params, log target)
cv_scores_rf = cross_val_score(rf_model, X_train, y_train_log, cv=5, scoring='r2')
print(f"Cross-validation R² scores: {[f'{score:.4f}' for score in cv_scores_rf]}")
print(f"Mean CV R² Score: {cv_scores_rf.mean():.4f} (+/- {cv_scores_rf.std():.4f})")

# Evaluate Gradient Boosting
print("\n" + "=" * 60)
print("GRADIENT BOOSTING MODEL EVALUATION")
print("=" * 60)
y_pred_gb_log = gb_model.predict(X_test)
y_pred_gb = np.exp(y_pred_gb_log)
mae_gb = mean_absolute_error(y_test_price, y_pred_gb)
rmse_gb = np.sqrt(mean_squared_error(y_test_price, y_pred_gb))
r2_gb = r2_score(y_test_price, y_pred_gb)

print(f"MAE (Mean Absolute Error): R{mae_gb:,.0f}")
print(f"RMSE (Root Mean Squared Error): R{rmse_gb:,.0f}")
print(f"R² Score: {r2_gb:.4f}")

# Cross-validation score for Gradient Boosting (best params, log target)
cv_scores_gb = cross_val_score(gb_model, X_train, y_train_log, cv=5, scoring='r2')
print(f"Cross-validation R² scores: {[f'{score:.4f}' for score in cv_scores_gb]}")
print(f"Mean CV R² Score: {cv_scores_gb.mean():.4f} (+/- {cv_scores_gb.std():.4f})")

# Select best model
print("\n" + "=" * 60)
print("MODEL COMPARISON & SELECTION")
print("=" * 60)
if r2_rf > r2_gb:
    best_model = rf_model
    best_model_name = "Random Forest"
    best_mae = mae_rf
    best_rmse = rmse_rf
    best_r2 = r2_rf
    print(f"✓ Random Forest selected as the best model")
else:
    best_model = gb_model
    best_model_name = "Gradient Boosting"
    best_mae = mae_gb
    best_rmse = rmse_gb
    best_r2 = r2_gb
    print(f"✓ Gradient Boosting selected as the best model")

print(f"\nBest Model: {best_model_name}")
print(f"Best MAE: R{best_mae:,.0f}")
print(f"Best RMSE: R{best_rmse:,.0f}")
print(f"Best R²: {best_r2:.4f}")

# Feature importance
print("\n" + "=" * 60)
print("FEATURE IMPORTANCE (Top 20)")
print("=" * 60)
# Attempt to extract feature names after preprocessing
try:
    preprocess_fitted = best_model.named_steps['preprocess']
    # Numeric feature names
    num_names = numeric_features
    # Categorical OHE names
    ohe = preprocess_fitted.named_transformers_['cat']
    cat_names = list(ohe.get_feature_names_out(categorical_features)) if categorical_features else []
    all_feature_names = num_names + cat_names
    importances = best_model.named_steps['model'].feature_importances_
    fi_df = pd.DataFrame({'feature': all_feature_names, 'importance': importances})
    fi_df = fi_df.sort_values('importance', ascending=False).head(20)
    print(fi_df.to_string(index=False))
except Exception as e:
    print(f"(Could not compute named importances: {str(e)})")

# Save metrics to JSON
metrics = {
    'timestamp': datetime.now().isoformat(),
    'best_model': best_model_name,
    'target_transform': 'log',
    'random_forest': {
        'mae': float(mae_rf),
        'rmse': float(rmse_rf),
        'r2': float(r2_rf),
        'cv_mean': float(cv_scores_rf.mean()),
        'cv_std': float(cv_scores_rf.std()),
        'best_params': rf_best_params
    },
    'gradient_boosting': {
        'mae': float(mae_gb),
        'rmse': float(rmse_gb),
        'r2': float(r2_gb),
        'cv_mean': float(cv_scores_gb.mean()),
        'cv_std': float(cv_scores_gb.std()),
        'best_params': gb_best_params
    },
    'data_info': {
        'total_samples': len(df),
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'features': numeric_features + categorical_features
    }
}

# Save best model
# Save best model
models_dir = os.path.join(script_dir, 'models')
os.makedirs(models_dir, exist_ok=True)
model_path = os.path.join(models_dir, 'airbnb_model.pkl')
with open(model_path, 'wb') as f:
    pickle.dump(best_model, f)

# Save scaler
# Scaler no longer used with tree models; save placeholder info
scaler_path = os.path.join(models_dir, 'scaler.pkl')
with open(scaler_path, 'wb') as f:
    pickle.dump({'note': 'Preprocessing handled in pipeline; scaler unused for trees'}, f)

# Save metrics
metrics_path = os.path.join(models_dir, 'metrics.json')
with open(metrics_path, 'w') as f:
    json.dump(metrics, f, indent=2)

print("\n" + "=" * 60)
print("MODEL SAVED")
print("=" * 60)
print(f"✓ Model saved to models/airbnb_model.pkl")
print(f"✓ Scaler saved to models/scaler.pkl")
print(f"✓ Metrics saved to models/metrics.json")

# Also save sample data for reference
data_dir = os.path.join(script_dir, 'data')
os.makedirs(data_dir, exist_ok=True)
sample_path = os.path.join(data_dir, 'sample_airbnb_data.csv')
df.to_csv(sample_path, index=False)
print(f"✓ Sample data saved to data/sample_airbnb_data.csv")