#!/usr/bin/env python3
"""
Comprehensive script to combine and clean all raw property data.
This script will:
1. Load all JSON files from raw_data folder
2. Remove duplicates
3. Clean and standardize data
4. Extract features
5. Save to a clean combined dataset
"""

import json
import pandas as pd
import numpy as np
import os
import glob
import re
from datetime import datetime

# Get script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
raw_data_dir = os.path.join(script_dir, 'raw_data')
data_dir = os.path.join(script_dir, 'data')

print("=" * 80)
print("PROPERTY DATA COMBINATION & CLEANING PIPELINE")
print("=" * 80)

# Step 1: Load all JSON files
print("\n[1/6] Loading raw data files...")
all_properties = []
file_pattern = os.path.join(raw_data_dir, '*.json')
json_files = glob.glob(file_pattern)

if not json_files:
    print(f"ERROR: No JSON files found in {raw_data_dir}")
    exit(1)

print(f"Found {len(json_files)} JSON files")

for json_file in sorted(json_files):
    filename = os.path.basename(json_file)
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                all_properties.extend(data)
                print(f"  ✓ {filename}: {len(data)} properties")
            else:
                print(f"  ⚠ {filename}: Unexpected format (not a list)")
    except Exception as e:
        print(f"  ✗ {filename}: Error - {str(e)}")

print(f"\nTotal properties loaded: {len(all_properties)}")

# Step 2: Remove duplicates
print("\n[2/6] Removing duplicates...")
unique_properties = {}

for prop in all_properties:
    if not isinstance(prop, dict):
        continue
    
    # Use listingNumber as unique ID, fallback to listingUrl
    prop_id = prop.get('listingNumber') or prop.get('listingUrl')
    
    if prop_id:
        # Keep the property with more data (more keys)
        if prop_id not in unique_properties or len(prop) > len(unique_properties[prop_id]):
            unique_properties[prop_id] = prop

print(f"Before deduplication: {len(all_properties)} properties")
print(f"After deduplication: {len(unique_properties)} properties")
print(f"Duplicates removed: {len(all_properties) - len(unique_properties)}")

# Convert back to list
all_properties = list(unique_properties.values())

# Step 3: Data quality check and filtering
print("\n[3/6] Filtering and quality checks...")
valid_properties = []
skipped_no_price = 0
skipped_invalid_price = 0
skipped_no_location = 0

for prop in all_properties:
    # Must have a price
    price = prop.get('price')
    if not price or price == 0:
        skipped_no_price += 1
        continue
    
    # Price must be reasonable (between 100k and 50M)
    if price < 100000 or price > 50000000:
        skipped_invalid_price += 1
        continue
    
    # Must have some location info
    if not prop.get('suburbName') and not prop.get('cityName'):
        skipped_no_location += 1
        continue
    
    valid_properties.append(prop)

print(f"Valid properties: {len(valid_properties)}")
print(f"Skipped - no price: {skipped_no_price}")
print(f"Skipped - invalid price: {skipped_invalid_price}")
print(f"Skipped - no location: {skipped_no_location}")

# Step 4: Extract and standardize features
print("\n[4/6] Extracting and standardizing features...")

def extract_features(property):
    """Extract standardized features from a property."""
    features = {}
    
    # Price (required)
    features['price'] = float(property.get('price', 0))
    
    # Bedrooms - try direct field first
    bedrooms = property.get('bedrooms', 0)
    if not bedrooms or bedrooms == 0:
        # Try keyFeatures
        for kf in property.get('keyFeatures', []):
            if isinstance(kf, dict) and kf.get('text') == 'Bedrooms':
                try:
                    bedrooms = int(float(kf.get('value', 0)))
                except (ValueError, TypeError):
                    pass
                break
    features['bedrooms'] = max(1, int(bedrooms) if bedrooms else 1)
    
    # Bathrooms - try direct field first
    bathrooms = property.get('bathrooms', 0)
    if not bathrooms or bathrooms == 0:
        for kf in property.get('keyFeatures', []):
            if isinstance(kf, dict) and kf.get('text') == 'Bathrooms':
                try:
                    bathrooms = float(kf.get('value', 0))
                except (ValueError, TypeError):
                    pass
                break
    features['bathrooms'] = max(1, int(bathrooms) if bathrooms else 1)
    
    # Accommodates - estimate
    features['accommodates'] = features['bedrooms'] * 2 + 1
    
    # Parking - combine parkingSpaces and garages
    parking = property.get('parkingSpaces', 0) or 0
    garages = property.get('garages', 0) or 0
    if garages == 0:
        for kf in property.get('keyFeatures', []):
            if isinstance(kf, dict) and kf.get('text') == 'Garages':
                try:
                    garages = int(float(kf.get('value', 0)))
                except (ValueError, TypeError):
                    pass
                break
    features['parking_spaces'] = float(parking + garages)
    
    # Amenities from keyFeatures and description
    key_features = property.get('keyFeatures', [])
    description = property.get('description', '') or ''
    description_lower = description.lower() if isinstance(description, str) else ''
    
    # Square meters - try multiple sources
    square_meters = 0
    size = property.get('size')
    if isinstance(size, (int, float)):
        square_meters = float(size)
    
    # If not found, try keyFeatures for floor size, erf size, stand size
    if square_meters == 0 and isinstance(key_features, list):
        for kf in key_features:
            if isinstance(kf, dict):
                text = kf.get('text', '').lower()
                value_str = str(kf.get('value', ''))
                # Look for floor size, erf size, stand size
                if any(keyword in text for keyword in ['floor size', 'building size', 'living space']):
                    try:
                        # Extract numeric value
                        nums = re.findall(r'\d+[,\s]?\d*', value_str.replace(',', ''))
                        if nums:
                            square_meters = float(nums[0].replace(' ', ''))
                            break
                    except (ValueError, TypeError, IndexError):
                        pass
    
    # If still not found, try description with regex
    if square_meters == 0 and isinstance(description, str):
        # Pattern: number followed by 'sqm', 'm²', 'm2', 'square meters'
        patterns = [
            r'(\d+[,\s]?\d*)\s*(?:sqm|m²|m2|square\s+meters?)(?!\s*erf|\s*stand)',
            r'(\d+[,\s]?\d*)\s*m²',
            r'(\d+[,\s]?\d*)\s*sqm'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, description.lower())
            if matches:
                try:
                    # Take the first match that looks reasonable (50-2000 sqm typical range)
                    for match in matches:
                        val = float(match.replace(',', '').replace(' ', ''))
                        if 50 <= val <= 2000:
                            square_meters = val
                            break
                    if square_meters > 0:
                        break
                except (ValueError, TypeError):
                    pass
    
    features['square_meters'] = square_meters
    
    # Pool
    pool = 0
    if isinstance(key_features, list):
        for kf in key_features:
            if isinstance(kf, dict) and 'pool' in kf.get('text', '').lower():
                pool = 1
                break
    if 'pool' in description_lower or 'swimming' in description_lower:
        pool = 1
    features['pool'] = pool
    
    # Garden
    garden = 0
    if isinstance(key_features, list):
        for kf in key_features:
            if isinstance(kf, dict):
                text = kf.get('text', '').lower()
                if 'garden' in text or 'patio' in text or 'yard' in text:
                    garden = 1
                    break
    if 'garden' in description_lower or 'patio' in description_lower or 'terrace' in description_lower:
        garden = 1
    features['garden'] = garden
    
    # Security
    security = 0
    if isinstance(key_features, list):
        for kf in key_features:
            if isinstance(kf, dict):
                text = kf.get('text', '').lower()
                if 'security' in text or 'alarm' in text or 'secure' in text:
                    security = 1
                    break
    if any(word in description_lower for word in ['security', 'alarm', 'gated', 'secure estate', 'access control']):
        security = 1
    features['security'] = security
    
    # Pet friendly
    pet_friendly = 0
    if isinstance(key_features, list):
        for kf in key_features:
            if isinstance(kf, dict) and 'pet' in kf.get('text', '').lower():
                pet_friendly = 1
                break
    if 'pet friendly' in description_lower or 'pets allowed' in description_lower:
        pet_friendly = 1
    features['pet_friendly'] = pet_friendly
    
    # Location features
    suburb = property.get('suburbName', '') or ''
    city = property.get('cityName', '') or ''
    suburb_lower = suburb.lower() if isinstance(suburb, str) else ''
    city_lower = city.lower() if isinstance(city, str) else ''
    
    # Near beach
    coastal_areas = ['hermanus', 'kleinmond', 'betty', 'pringle', 'hawston', 'rooi els', 
                     'franskraal', 'pearly', 'gansbaai', 'overstrand', 'stanford', 'onrus']
    near_beach = 0
    if any(area in suburb_lower or area in city_lower for area in coastal_areas):
        near_beach = 1
    if any(word in description_lower for word in ['beach', 'ocean', 'sea view', 'seaside', 'coastal']):
        near_beach = 1
    features['near_beach'] = near_beach
    
    # Location score (1-10 based on desirability)
    location_score = 7  # default
    if 'hermanus' in suburb_lower or 'hermanus' in city_lower:
        location_score = 9
    elif 'kleinmond' in suburb_lower or 'kleinmond' in city_lower:
        location_score = 8
    elif 'betty' in suburb_lower or 'stanford' in suburb_lower:
        location_score = 8
    elif 'gansbaai' in suburb_lower:
        location_score = 7
    features['location_score'] = location_score
    
    # Property age (default, can't determine from data)
    features['property_age'] = 10
    
    # Metadata features
    features['description_length'] = len(description) if isinstance(description, str) else 0
    photos = property.get('photos', [])
    features['num_photos'] = len(photos) if isinstance(photos, list) else 0
    features['has_agency'] = 1 if property.get('agencyName') else 0
    
    # Property type
    property_type = property.get('propertyTypeId', 0)
    features['property_type_id'] = int(property_type) if property_type else 0
    
    # Location data for reference
    features['suburb'] = suburb
    features['city'] = city
    features['listing_number'] = property.get('listingNumber', '')
    features['listing_url'] = property.get('listingUrl', '')
    
    return features

# Process all properties
processed_features = []
errors = 0

for idx, prop in enumerate(valid_properties):
    try:
        feat = extract_features(prop)
        processed_features.append(feat)
    except Exception as e:
        errors += 1
        if errors <= 5:
            print(f"  Error processing property {idx}: {str(e)}")

print(f"Successfully processed: {len(processed_features)} properties")
if errors > 0:
    print(f"Errors encountered: {errors}")

# Step 5: Create DataFrame and additional cleaning
print("\n[5/6] Creating clean dataset...")
df = pd.DataFrame(processed_features)

# Remove extreme outliers using IQR method
Q1 = df['price'].quantile(0.25)
Q3 = df['price'].quantile(0.75)
IQR = Q3 - Q1
lower_bound = Q1 - 3 * IQR
upper_bound = Q3 + 3 * IQR

before_outlier_removal = len(df)
df = df[(df['price'] >= lower_bound) & (df['price'] <= upper_bound)]
outliers_removed = before_outlier_removal - len(df)

print(f"Outliers removed (3*IQR method): {outliers_removed}")

# Sort by price for easier analysis
df = df.sort_values('price').reset_index(drop=True)

# Step 6: Save cleaned data
print("\n[6/6] Saving cleaned dataset...")

# Save the main feature set (for ML)
feature_columns = ['price', 'bedrooms', 'bathrooms', 'accommodates', 'parking_spaces', 
                   'square_meters', 'pool', 'garden', 'security', 'pet_friendly',
                   'near_beach', 'location_score', 'property_age', 
                   'description_length', 'num_photos', 'has_agency', 'property_type_id']

df_features = df[feature_columns]
feature_path = os.path.join(data_dir, 'property24_data.csv')
df_features.to_csv(feature_path, index=False)
print(f"✓ Feature dataset saved: {feature_path}")

# Save full dataset with metadata (for reference)
full_path = os.path.join(data_dir, 'property24_data_full.csv')
df.to_csv(full_path, index=False)
print(f"✓ Full dataset saved: {full_path}")

# Save summary statistics
print("\n" + "=" * 80)
print("DATASET SUMMARY")
print("=" * 80)
print(f"\nTotal properties: {len(df)}")
print(f"\nPrice Statistics (ZAR):")
print(f"  Mean: R{df['price'].mean():,.0f}")
print(f"  Median: R{df['price'].median():,.0f}")
print(f"  Std Dev: R{df['price'].std():,.0f}")
print(f"  Min: R{df['price'].min():,.0f}")
print(f"  Max: R{df['price'].max():,.0f}")

print(f"\nProperty Characteristics:")
print(f"  Avg Bedrooms: {df['bedrooms'].mean():.1f}")
print(f"  Avg Bathrooms: {df['bathrooms'].mean():.1f}")
print(f"  Avg Parking Spaces: {df['parking_spaces'].mean():.1f}")
print(f"  Properties with Pool: {df['pool'].sum()} ({df['pool'].sum()/len(df)*100:.1f}%)")
print(f"  Properties with Garden: {df['garden'].sum()} ({df['garden'].sum()/len(df)*100:.1f}%)")
print(f"  Properties with Security: {df['security'].sum()} ({df['security'].sum()/len(df)*100:.1f}%)")
print(f"  Pet Friendly Properties: {df['pet_friendly'].sum()} ({df['pet_friendly'].sum()/len(df)*100:.1f}%)")
print(f"  Properties Near Beach: {df['near_beach'].sum()} ({df['near_beach'].sum()/len(df)*100:.1f}%)")

print(f"\nTop Locations:")
location_counts = df['suburb'].value_counts().head(5)
for suburb, count in location_counts.items():
    print(f"  {suburb}: {count} properties")

print(f"\nData Quality:")
print(f"  Avg photos per property: {df['num_photos'].mean():.1f}")
print(f"  Avg description length: {df['description_length'].mean():.0f} chars")
print(f"  Properties with agency: {df['has_agency'].sum()} ({df['has_agency'].sum()/len(df)*100:.1f}%)")

# Sample-to-feature ratio for ML
num_features = len(feature_columns) - 1  # exclude price
ratio = len(df) / num_features
print(f"\nML Readiness:")
print(f"  Features: {num_features}")
print(f"  Sample-to-Feature Ratio: {ratio:.1f}:1")
if ratio >= 10:
    print(f"  ✓ Good ratio for machine learning (>10:1)")
elif ratio >= 5:
    print(f"  ⚠ Acceptable ratio, but more data would help")
else:
    print(f"  ✗ Low ratio, collect more data for better models")

print("\n" + "=" * 80)
print("✅ DATA COMBINATION AND CLEANING COMPLETE!")
print("=" * 80)
print(f"\nNext step: Run 'python model_training.py' to train with the new dataset")
