# Overberg Property Analyzer

A machine learning tool for analysing and predicting property prices in South Africa's Overstrand region — built on real listing data scraped from Property24.

---

## The Problem

If you're buying, selling, or renting out a property in a coastal town like Hermanus or Bettys Bay, it's genuinely hard to know whether an asking price is fair. Estate agents have their own interests, comparable sales data is buried, and the market is hyperlocal — a property one suburb over can be priced completely differently.

This project builds a data-driven answer to the question: *is this property priced above or below what the market supports?*

---

## What It Does

- **Predicts market value** for a property based on 17 features: bedrooms, bathrooms, suburb, property type, amenities, listing quality signals, and more
- **Valuation assessment** — tells you whether a listing is undervalued, fairly priced, or overpriced relative to the model's prediction
- **Market comparison** — shows where the property sits in the price distribution of similar listings
- **Interactive Streamlit app** — enter any property's details and get an instant analysis

---

## Tech Stack

| Layer | Tools |
|-------|-------|
| Data collection | Apify (Property24 scraper) |
| Data processing | Python, pandas, regex |
| Modelling | scikit-learn (Random Forest), log-target transform, RandomizedSearchCV |
| App | Streamlit, Plotly |
| Deployment | Docker |

---

## The Data

- **685 unique property listings** scraped from Property24 across the Overstrand region
- **Coverage:** Hermanus, Vermont, Sandbaai, Onrus, Bettys Bay, Kleinbaai, and surrounding suburbs
- **Price range:** R290,000 – R15,850,000
- **Raw files:** 22 JSON scrape outputs totalling 2,182 listings (duplicates removed)

---

## Model Performance

| Metric | Value |
|--------|-------|
| R² Score | 0.45 |
| MAE | ±R1,304,153 (~29% of mean price) |
| CV R² (log-space) | 0.49 ± 0.24 |
| Training samples | 685 properties |

The model is best used for **comparative analysis** — identifying significantly over- or under-priced listings — rather than exact valuations. A 29% typical error is meaningful context when the mean price is R4.5M.

**Top predictive features:** number of photos, description length, bathrooms, property type, parking spaces, bedrooms, square metres, suburb.

---

## How to Run

**Requirements:** Python 3.9+, pip

```bash
# 1. Clone the repo
git clone https://github.com/rpvermaak/overstrand-property-analyzer.git
cd overstrand-property-analyzer

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Retrain the model on the included data
python model_training.py

# 4. Launch the app
streamlit run app.py
```

Or with Docker:
```bash
docker build -t property-analyzer .
docker run -p 8501:8501 property-analyzer
```

---

## Project Structure

```
overstrand-airbnb-analyzer/
├── app.py                  # Streamlit app
├── model_training.py       # Model training pipeline
├── process_data.py         # Data cleaning and feature engineering
├── combine_clean_data.py   # Merges raw scrape files
├── models/
│   ├── airbnb_model.pkl    # Trained Random Forest pipeline
│   ├── scaler.pkl          # Feature scaler
│   └── metrics.json        # Model performance metrics
├── data/
│   ├── property24_data_full.csv   # 685 cleaned listings
│   └── combined_property_data.json
├── raw_data/               # 22 raw Property24 JSON scrapes
├── Dockerfile
└── requirements.txt
```

---

## What I Learned

Getting from a raw JSON scrape to a working valuation model involved more data cleaning than modelling. Key challenges:

- **Duplicate handling:** The scraper produced overlapping pages; had to deduplicate on listing ID across 22 files
- **Square metre extraction:** Size data was buried in listing description text — had to regex-parse it from prose
- **Location encoding:** Adding suburb + city one-hot encoding was the single biggest R² jump (0.27 → 0.45)
- **Log-target transform:** Raw price predictions had high variance at the top end; log-transforming the target stabilised predictions across the price range

---

## Limitations

This model is specific to the **Overstrand region** and trained on data from **January 2026**. It is not suitable for general South African property valuation and should not be the sole basis for investment decisions. Always consult a registered property professional.

---

*Built by [Ruben Vermaak](https://github.com/rpvermaak) · January 2026*
