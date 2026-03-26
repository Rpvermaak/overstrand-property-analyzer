import json
import pandas as pd
import numpy as np
import os
from datetime import datetime

# Get the directory of this script
script_dir = os.path.dirname(os.path.abspath(__file__))

# Load the scraped data - try combined dataset first, fall back to original
data_files = [
    os.path.join(script_dir, 'data/combined_property_data.json'),
    os.path.join(script_dir, 'data/dataset_property24-scraper_2026-01-23_04-15-33-666.json')
]

data = []
data_file_used = None
for data_file in data_files:
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            data = json.load(f)
        data_file_used = os.path.basename(data_file)
        print(f"✓ Loaded {len(data)} raw properties from {data_file_used}")
        break

if not data:
    raise FileNotFoundError("No property data files found!")

print("=" * 60)

# Function to extract features from a property
def extract_features(property):
    features = {}
    
    # Check if property is a dictionary (it should be)
    if not isinstance(property, dict):
        return None
    
    # Basic info - try direct fields first (new format), then fall back to old format
    features['price'] = property.get('price', 0)
    if features['price'] == 0 or features['price'] is None:
        return None  # Skip if no price
    
    # Bedrooms - try direct field first
    bedrooms = property.get('bedrooms', 0)
    if bedrooms is None or bedrooms == 0:
        # Fall back to keyFeatures
        for kf in property.get('keyFeatures', []):
            if kf.get('text') == 'Bedrooms':
                try:
                    bedrooms = int(float(kf.get('value', 0)))
                except (ValueError, TypeError):
                    bedrooms = 0
                break
    features['bedrooms'] = max(1, int(bedrooms) if bedrooms else 1)  # At least 1 bedroom
    
    # Bathrooms - try direct field first
    bathrooms = property.get('bathrooms', 0)
    if bathrooms is None or bathrooms == 0:
        # Fall back to keyFeatures
        for kf in property.get('keyFeatures', []):
            if kf.get('text') == 'Bathrooms':
                try:
                    bathrooms = float(kf.get('value', 0))
                except (ValueError, TypeError):
                    bathrooms = 0
                break
    features['bathrooms'] = max(1, int(bathrooms) if bathrooms else 1)  # At least 1 bathroom
    
    # Accommodates - estimate as bedrooms * 2 + 1
    features['accommodates'] = features['bedrooms'] * 2 + 1
    
    # Parking spaces - try direct fields first
    parking_spaces = property.get('parkingSpaces', 0)
    if parking_spaces is None:
        parking_spaces = 0
    garages = property.get('garages', 0)
    if garages is None:
        garages = 0
    # Also check keyFeatures for garages
    if garages == 0:
        for kf in property.get('keyFeatures', []):
            if kf.get('text') == 'Garages':
                try:
                    garages = int(float(kf.get('value', 0)))
                except (ValueError, TypeError):
                    garages = 0
                break
    features['parking_spaces'] = float(parking_spaces + garages)
    
    # Square meters (floor size)
    square_meters = 0
    size = property.get('size', {})
    if isinstance(size, dict):
        if size.get('sizeType') == 'Floor' and size.get('unit') == 'm²':
            try:
                square_meters = float(size.get('value', 0))
            except (ValueError, TypeError):
                square_meters = 0
    features['square_meters'] = square_meters
    
    # Pool - check if mentioned in keyFeatures or description
    pool = 0
    key_features = property.get('keyFeatures', [])
    if isinstance(key_features, list):
        for kf in key_features:
            if isinstance(kf, dict) and 'pool' in kf.get('text', '').lower():
                pool = 1
                break
    description = property.get('description', '')
    if description and isinstance(description, str):
        description_lower = description.lower()
        if 'pool' in description_lower or 'swimming' in description_lower:
            pool = 1
    features['pool'] = pool
    
    # Garden/outdoor space
    garden = 0
    if isinstance(key_features, list):
        for kf in key_features:
            if isinstance(kf, dict):
                text = kf.get('text', '').lower()
                if 'garden' in text or 'patio' in text:
                    garden = 1
                    break
    if description and isinstance(description, str):
        if 'garden' in description_lower or 'patio' in description_lower or 'terrace' in description_lower:
            garden = 1
    features['garden'] = garden
    
    # Security features
    security = 0
    if isinstance(key_features, list):
        for kf in key_features:
            if isinstance(kf, dict):
                text = kf.get('text', '').lower()
                if 'security' in text or 'alarm' in text:
                    security = 1
                    break
    if description and isinstance(description, str):
        if 'security' in description_lower or 'alarm' in description_lower or 'gated' in description_lower:
            security = 1
    features['security'] = security
    
    # Near beach - based on suburb or description
    near_beach = 0
    coastal_suburbs = ['hawston', 'hermanus', 'kleinmond', 'betty', 'pringle', 'rooi els', 'franskraal', 'pearly', 'gansbaai', 'overstrand']
    suburb = property.get('suburbName', '')
    if suburb and isinstance(suburb, str):
        suburb_lower = suburb.lower()
        if any(cs in suburb_lower for cs in coastal_suburbs):
            near_beach = 1
    if description and isinstance(description, str) and ('beach' in description_lower or 'seaside' in description_lower):
        near_beach = 1
    features['near_beach'] = near_beach
    
    # Location score - based on suburb
    location_score = 7  # default
    if suburb and isinstance(suburb, str):
        suburb_lower = suburb.lower()
        if 'hermanus' in suburb_lower or 'hawston' in suburb_lower or 'overstrand' in suburb_lower:
            location_score = 9
        elif 'kleinmond' in suburb_lower or 'betty' in suburb_lower:
            location_score = 8
        elif 'swellendam' in suburb_lower:
            location_score = 6
        elif 'gansbaai' in suburb_lower:
            location_score = 7
    features['location_score'] = location_score
    
    # Property age - not available, estimate based on description or use default
    features['property_age'] = 10
    
    # Description length (proxy for how well-listed the property is)
    features['description_length'] = len(description) if description and isinstance(description, str) else 0
    
    # Number of photos (indicates property quality/investment)
    photos = property.get('photos', [])
    features['num_photos'] = len(photos) if isinstance(photos, list) else 0
    
    # Agency presence (some agencies are more reputable)
    features['has_agency'] = 1 if property.get('agencyName') else 0
    
    return features

# Extract features for all properties
properties = []
errors = 0
for idx, prop in enumerate(data):
    try:
        if not isinstance(prop, dict):
            print(f"Warning: Property {idx} is type {type(prop)}, not dict. Skipping.")
            errors += 1
            continue
        feat = extract_features(prop)
        if feat:
            properties.append(feat)
    except Exception as e:
        errors += 1
        if errors <= 5:  # Only print first 5 detailed errors
            print(f"Error processing property {idx}: {str(e)}")

print(f"Successfully extracted features from {len(properties)} properties")
print(f"Skipped {len(data) - len(properties)} properties (missing data)")
if errors > 0:
    print(f"Errors: {errors}")

# Create DataFrame
df = pd.DataFrame(properties)

# Filter out properties with price > 10M or < 100k (outliers)
df_before = len(df)
df = df[(df['price'] > 100000) & (df['price'] < 10000000)]
print(f"\nRemoved {df_before - len(df)} outliers (outside price range)")

# Basic statistics
print("\n" + "=" * 60)
print("DATA STATISTICS")
print("=" * 60)
print(f"Total properties in dataset: {len(df)}")
print(f"\nPrice Statistics (ZAR):")
print(f"  Mean: R{df['price'].mean():,.0f}")
print(f"  Median: R{df['price'].median():,.0f}")
print(f"  Min: R{df['price'].min():,.0f}")
print(f"  Max: R{df['price'].max():,.0f}")
print(f"\nProperty Features:")
print(f"  Avg Bedrooms: {df['bedrooms'].mean():.1f}")
print(f"  Avg Bathrooms: {df['bathrooms'].mean():.1f}")
print(f"  Properties with Pool: {df['pool'].sum()} ({df['pool'].sum()/len(df)*100:.1f}%)")
print(f"  Properties with Garden: {df['garden'].sum()} ({df['garden'].sum()/len(df)*100:.1f}%)")
print(f"  Properties with Security: {df['security'].sum()} ({df['security'].sum()/len(df)*100:.1f}%)")
print(f"  Properties Near Beach: {df['near_beach'].sum()} ({df['near_beach'].sum()/len(df)*100:.1f}%)")

# Save to CSV
csv_path = os.path.join(script_dir, 'data/property24_data.csv')
df.to_csv(csv_path, index=False)
print(f"\n✓ Processed data saved to data/property24_data.csv")
print(f"Features: {list(df.columns)}")