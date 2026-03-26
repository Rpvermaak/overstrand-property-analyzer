import streamlit as st
import pickle
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import os
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim, ArcGIS

# Helper: robust geocoding with fallbacks
def geocode_address(address: str):
    variants = [
        address,
        f"{address}, Overstrand, Western Cape, South Africa",
        f"{address}, Western Cape, South Africa",
        f"{address}, South Africa",
    ]
    # Try Nominatim first (biased to ZA)
    try:
        nm = Nominatim(user_agent="overstrand_airbnb_analyzer")
        for v in variants:
            loc = nm.geocode(
                query=v,
                country_codes="za",
                addressdetails=True,
                exactly_one=True,
                timeout=10,
            )
            if loc:
                return loc.latitude, loc.longitude, loc.address, "Nominatim"
    except Exception:
        pass
    # Fallback: ArcGIS (robust global geocoder)
    try:
        arc = ArcGIS(timeout=10)
        loc = arc.geocode(address, out_fields="*", maxLocations=1)
        if not loc:
            for v in variants[1:]:
                loc = arc.geocode(v, out_fields="*", maxLocations=1)
                if loc:
                    break
        if loc:
            # ArcGIS uses attributes differently; build a readable address
            resolved = getattr(loc, "address", None) or str(loc)
            return loc.latitude, loc.longitude, resolved, "ArcGIS"
    except Exception:
        pass
    return None

# Get working directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Load the saved model (pipeline with preprocessing)
try:
    model_path = os.path.join(script_dir, 'models/airbnb_model.pkl')
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
except Exception as e:
    st.error(f"Error loading model: {e}")
    st.stop()

# Load full data for comparisons (includes location)
try:
    data_path = os.path.join(script_dir, 'data/property24_data_full.csv')
    df = pd.read_csv(data_path)
    # Use the most common property type as a sensible default so the user
    # doesn't need to look it up on Property24 listings.
    property_type_default = int(df['property_type_id'].mode().iloc[0])
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

st.set_page_config(page_title="AirBnB Property Analyzer", page_icon="🏠", layout="wide")

st.title("Property Price Analyzer")
st.markdown("Analyze property prices in the Overstrand area")

# Sidebar - Property Inputs
with st.sidebar:
    # Logo at top of sidebar

    logo_path = os.path.join(script_dir, 'Logo/Overberg.svg')
    st.image(logo_path, width=200)
    
    st.header("Property Details")

    # Basic Property Info
    listing_price = st.number_input("Asking Price (R)", min_value=0, value=3000000, step=50000)
    bedrooms = st.slider("Bedrooms", 1, 6, 3)
    bathrooms = st.slider("Bathrooms", 1, 4, 2)
    accommodates = st.slider("Guest Capacity", 2, 10, 6)
    parking_spaces = st.slider("Parking Spaces", 0, 5, 2)
    square_meters = st.number_input("Square Meters", min_value=0, value=150, step=5)

    st.subheader("Amenities & Location")
    pool = st.checkbox("Swimming Pool", value=True)
    garden = st.checkbox("Garden/Patio", value=True)
    security = st.checkbox("Security Features", value=False)
    pet_friendly = st.checkbox("Pet Friendly", value=False)
    near_beach = st.checkbox("Beach Access", value=True)
    location_score = st.slider("Location Score (1-10)", 1, 10, 7, help="1=Poor location, 10=Prime location")
    property_age = st.slider("Property Age (years)", 0, 50, 10)
    
    st.subheader("Marketing & Listing")
    description_length = st.slider("Description Length (chars)", 0, 3000, 1400)
    num_photos = st.slider("Number of Photos", 0, 60, 30)
    has_agency = st.checkbox("Listed by Agency", value=True)
    
    st.subheader("Location")
    
    # Initialize session state for coordinates and location
    if 'latitude' not in st.session_state:
        st.session_state.latitude = -34.4269
    if 'longitude' not in st.session_state:
        st.session_state.longitude = 19.2520
    if 'suburb' not in st.session_state:
        st.session_state.suburb = None
    if 'city' not in st.session_state:
        st.session_state.city = None
    
    # Address input
    address = st.text_input("Enter Address", value="Overstrand, South Africa", 
                           help="Enter full address (street, city, country)")
    
    # Geocode address button
    if st.button("Find Location", key="geocode_btn"):
        if address:
            result = geocode_address(address)
            if result:
                lat, lng, resolved, provider = result
                # If within rough ZA bounds, accept; otherwise warn but still set
                within_za = (-35.5 <= lat <= -21.5) and (15.5 <= lng <= 33.5)
                st.session_state.latitude = lat
                st.session_state.longitude = lng
                st.session_state.resolved_address = resolved
                st.session_state.geo_provider = provider
                
                # Try to extract suburb and city from resolved address
                # Address format is typically: "street, suburb, city, province, country"
                address_parts = [part.strip() for part in resolved.split(',')]
                if len(address_parts) >= 2:
                    # The second-to-last part is usually the suburb/area
                    potential_suburb = address_parts[-3] if len(address_parts) >= 3 else address_parts[-2]
                    st.session_state.suburb = potential_suburb
                if len(address_parts) >= 2:
                    # The part before country is usually the city/province
                    potential_city = address_parts[-2] if len(address_parts) >= 2 else address_parts[-1]
                    st.session_state.city = potential_city
                
                if within_za:
                    st.success(f"✓ Found ({provider}): {resolved}")
                else:
                    st.warning(f"Found outside ZA bounds ({provider}): {resolved}. Please verify.")
                # Force immediate UI refresh so map re-centers
                st.rerun()
            else:
                st.warning("Address not found via Nominatim/ArcGIS. Please refine the address or enter coordinates manually.")
    
    # Use auto-populated suburb and city from geocoding, or defaults
    suburbs = sorted(df['suburb'].dropna().unique().astype(str))
    suburb = st.session_state.suburb if st.session_state.suburb and st.session_state.suburb in suburbs else suburbs[0] if suburbs else None
    
    cities = sorted(df['city'].dropna().unique().astype(str))
    city = st.session_state.city if st.session_state.city and st.session_state.city in cities else cities[0] if cities else None
    
    st.header("Investment Analysis")
    
    st.subheader("Loan Details")
    down_payment_pct = st.slider("Down Payment %", 0, 100, 20, step=5)
    interest_rate = st.number_input("Annual Interest Rate %", min_value=0.0, value=11.5, step=0.25)
    loan_term_years = st.slider("Loan Term (years)", 5, 30, 20)
    
    st.subheader("Revenue Assumptions")
    avg_nightly_rate = st.number_input("Avg Nightly Rate (R)", min_value=0, value=1500, step=100)
    occupancy_rate = st.slider("Expected Occupancy %", 0, 100, 60, step=5)
    
    st.subheader("Operating Expenses")
    property_tax_annual = st.number_input("Annual Property Tax (R)", min_value=0, value=12000, step=1000)
    insurance_annual = st.number_input("Annual Insurance (R)", min_value=0, value=8000, step=1000)
    maintenance_pct = st.slider("Maintenance % of Revenue", 0, 50, 10, step=5)
    management_pct = st.slider("Management % of Revenue", 0, 50, 15, step=5)
    utilities_monthly = st.number_input("Monthly Utilities (R)", min_value=0, value=2000, step=500)
    cleaning_per_booking = st.number_input("Cleaning per Booking (R)", min_value=0, value=500, step=100)
    


# Initialize session state for analysis results
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False
if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}
if 'last_input_hash' not in st.session_state:
    st.session_state.last_input_hash = None

# Create a hash of current inputs to detect changes
current_inputs = {
    'bedrooms': bedrooms,
    'bathrooms': bathrooms,
    'accommodates': accommodates,
    'parking_spaces': parking_spaces,
    'square_meters': square_meters,
    'pool': pool,
    'garden': garden,
    'security': security,
    'near_beach': near_beach,
    'location_score': location_score,
    'property_age': property_age,
    'description_length': description_length,
    'num_photos': num_photos,
    'has_agency': has_agency,
    'listing_price': listing_price,
    'avg_nightly_rate': avg_nightly_rate,
    'occupancy_rate': occupancy_rate
}
import hashlib
input_hash = hashlib.md5(str(current_inputs).encode()).hexdigest()

# Reset analysis if inputs changed
if st.session_state.last_input_hash != input_hash:
    st.session_state.analysis_complete = False
    st.session_state.last_input_hash = input_hash

# Display saved analysis results if they exist
if st.session_state.analysis_complete:
    st.info("📊 Showing analysis results from previous calculation. Change inputs and click 'Analyze Property' to refresh.")

# Use a form to prevent reruns on every widget change
with st.form("analysis_form"):
    st.subheader("Review & Analyze")
    
    if st.form_submit_button("🔍 Analyze Property", type="primary", use_container_width=True):
        st.session_state.should_analyze = True

# Only run analysis if button was clicked or analysis is already complete
if st.session_state.get('should_analyze') or st.session_state.analysis_complete:
    try:
            # Prepare input features
            input_data = pd.DataFrame([{
                'bedrooms': int(bedrooms),
                'bathrooms': int(bathrooms),
                'accommodates': int(accommodates),
                'parking_spaces': int(parking_spaces),
                'square_meters': float(square_meters),
                'pool': int(pool),
                'garden': int(garden),
                'security': int(security),
                'near_beach': int(near_beach),
                'location_score': int(location_score),
                'property_age': int(property_age),
                'description_length': int(description_length),
                'num_photos': int(num_photos),
                'has_agency': int(has_agency),
                'suburb': str(suburb),
                'city': str(city),
                'property_type_id': int(property_type_default)
            }])

            # Prediction (model returns log price)
            predicted_log_price = model.predict(input_data)[0]
            predicted_price = np.exp(predicted_log_price)
            valuation_diff = predicted_price - listing_price
            is_undervalued = valuation_diff > 0
            
            # Store key values in session state
            st.session_state.predicted_price = predicted_price
            st.session_state.listing_price = listing_price
            st.session_state.valuation_diff = valuation_diff
            st.session_state.is_undervalued = is_undervalued
            st.session_state.analysis_complete = True
            st.session_state.should_analyze = False  # Reset flag after analysis

            # Dashboard Layout
            st.success("Analysis Complete!")

            # Key Metrics Row
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Predicted Price", f"R{predicted_price:,.0f}")
            with col2:
                st.metric("Asking Price", f"R{listing_price:,.0f}")
            with col3:
                st.metric("Difference", f"R{valuation_diff:,.0f}")
            with col4:
                st.metric("Valuation", "Undervalued" if is_undervalued else "Overpriced")

            st.divider()
            
            # Calculate Investment Metrics
            down_payment = listing_price * (down_payment_pct / 100)
            loan_amount = listing_price - down_payment
            monthly_rate = (interest_rate / 100) / 12
            num_payments = loan_term_years * 12
            
            # Monthly mortgage payment
            if loan_amount > 0 and monthly_rate > 0:
                monthly_mortgage = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
            else:
                monthly_mortgage = 0
            
            # Revenue calculations
            nights_per_month = 30 * (occupancy_rate / 100)
            monthly_revenue = avg_nightly_rate * nights_per_month
            annual_revenue = monthly_revenue * 12
            
            # Operating expenses
            monthly_maintenance = (monthly_revenue * maintenance_pct / 100)
            monthly_management = (monthly_revenue * management_pct / 100)
            bookings_per_month = nights_per_month / 2.5  # Avg 2.5 night stay
            monthly_cleaning = cleaning_per_booking * bookings_per_month
            monthly_property_tax = property_tax_annual / 12
            monthly_insurance = insurance_annual / 12
            
            total_monthly_expenses = (
                monthly_mortgage + 
                monthly_maintenance + 
                monthly_management + 
                monthly_cleaning + 
                utilities_monthly + 
                monthly_property_tax + 
                monthly_insurance
            )
            
            # NOI (Net Operating Income - before debt service)
            annual_operating_expenses = (
                monthly_maintenance + 
                monthly_management + 
                monthly_cleaning + 
                utilities_monthly + 
                monthly_property_tax + 
                monthly_insurance
            ) * 12
            noi = annual_revenue - annual_operating_expenses
            
            # Cash flow
            monthly_cashflow = monthly_revenue - total_monthly_expenses
            annual_cashflow = monthly_cashflow * 12
            
            # ROI metrics
            total_cash_invested = down_payment
            if total_cash_invested > 0:
                coc_return = (annual_cashflow / total_cash_invested) * 100
                cap_rate = (noi / listing_price) * 100
            else:
                coc_return = 0
                cap_rate = 0
            
            # Simple ROI
            if total_cash_invested > 0:
                roi = (annual_cashflow / total_cash_invested) * 100
            else:
                roi = 0
            
            # Calculate Investment Score (1-10)
            score_components = []
            
            # 1. Cash flow score (max 2 points)
            if monthly_cashflow > 10000:
                score_components.append(2.0)
            elif monthly_cashflow > 5000:
                score_components.append(1.5)
            elif monthly_cashflow > 0:
                score_components.append(1.0)
            else:
                score_components.append(0.0)
            
            # 2. CoC Return score (max 2 points)
            if coc_return > 15:
                score_components.append(2.0)
            elif coc_return > 10:
                score_components.append(1.5)
            elif coc_return > 5:
                score_components.append(1.0)
            else:
                score_components.append(0.0)
            
            # 3. Cap Rate score (max 2 points)
            if cap_rate > 8:
                score_components.append(2.0)
            elif cap_rate > 6:
                score_components.append(1.5)
            elif cap_rate > 4:
                score_components.append(1.0)
            else:
                score_components.append(0.0)
            
            # 4. Valuation score (max 2 points)
            valuation_pct = ((predicted_price - listing_price) / listing_price) * 100
            if valuation_pct > 10:
                score_components.append(2.0)
            elif valuation_pct > 0:
                score_components.append(1.5)
            elif valuation_pct > -10:
                score_components.append(1.0)
            else:
                score_components.append(0.0)
            
            # 5. Property features score (max 2 points)
            feature_score = 0
            if pool: feature_score += 0.3
            if garden: feature_score += 0.2
            if security: feature_score += 0.2
            if near_beach: feature_score += 0.4
            if location_score >= 7: feature_score += 0.4
            if bedrooms >= 3: feature_score += 0.3
            if parking_spaces >= 2: feature_score += 0.2
            score_components.append(min(feature_score, 2.0))
            
            investment_score = sum(score_components)

            # Analysis Tabs
            tab1, tab2, tab3, tab4 = st.tabs(["Valuation", "Market Comparison", "Investment Analytics", "Details"])

            with tab1:
                st.subheader("Valuation Analysis")

                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Predicted Price", f"R{predicted_price:,.0f}")
                    st.metric("Asking Price", f"R{listing_price:,.0f}")
                    st.metric("Difference", f"R{valuation_diff:,.0f}")

                with col2:
                    if is_undervalued:
                        st.success("GOOD VALUE - Priced below predicted value")
                    else:
                        st.warning("OVERPRICED - Priced above predicted value")

                # Price Comparison Chart
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=['Asking Price', 'Predicted Price'],
                    y=[listing_price, predicted_price],
                    marker_color=['red' if not is_undervalued else 'green', 'blue']
                ))
                fig.update_layout(title="Price Comparison", height=400)
                st.plotly_chart(fig, use_container_width=True)

            with tab2:
                st.subheader("Market Comparison")

                # Filter similar properties
                similar = df[
                    (df['bedrooms'] == bedrooms) &
                    (df['bathrooms'].between(bathrooms-1, bathrooms+1)) &
                    (df['accommodates'].between(accommodates-2, accommodates+2))
                ]

                if len(similar) > 0:
                    st.metric("Similar Properties", len(similar))

                    col1, col2 = st.columns(2)
                    with col1:
                        avg_price = similar['price'].mean()
                        st.metric("Avg Price (Similar)", f"R{avg_price:,.0f}")
                        diff = predicted_price - avg_price
                        st.metric("vs Market", f"R{diff:,.0f}")

                    with col2:
                        percentile = (predicted_price > df['price']).mean() * 100
                        st.metric("Price Percentile", f"{percentile:.0f}%")

                    # Distribution plot
                    fig = px.histogram(df, x="price", nbins=20, title="Market Price Distribution")
                    fig.add_vline(x=predicted_price, line_dash="dash", line_color="red")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No similar properties found in database")

            with tab3:
                st.subheader("AirBnB Investment Analytics")
                
                # Investment Score
                score_color = "green" if investment_score >= 7 else "orange" if investment_score >= 5 else "red"
                
                # Create a prominent score display
                score_col1, score_col2, score_col3 = st.columns([1, 2, 1])
                with score_col2:
                    st.metric("Investment Score", f"{investment_score:.1f}/10")
                
                if investment_score >= 7:
                    st.success("EXCELLENT - Strong investment opportunity!")
                elif investment_score >= 5:
                    st.warning("MODERATE - Decent opportunity with some considerations")
                else:
                    st.error("POOR - Weak investment potential")
                
                st.divider()
                
                # Key Investment Metrics
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Monthly Cash Flow", f"R{monthly_cashflow:,.0f}", 
                             delta="Positive" if monthly_cashflow > 0 else "Negative")
                with col2:
                    st.metric("CoC Return", f"{coc_return:.1f}%")
                with col3:
                    st.metric("Cap Rate", f"{cap_rate:.1f}%")
                with col4:
                    st.metric("Annual NOI", f"R{noi:,.0f}")
                
                st.divider()
                
                # Financial Details
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("**Revenue**")
                    st.write(f"Nightly Rate: R{avg_nightly_rate:,.0f}")
                    st.write(f"**Occupancy:** {occupancy_rate}% ({nights_per_month:.0f} nights/month)")
                    st.write(f"**Monthly Revenue:** R{monthly_revenue:,.0f}")
                    st.write(f"Annual Gross Revenue: R{annual_revenue:,.0f}")
                    
                    st.markdown("**Financing**")
                    st.write(f"Purchase Price: R{listing_price:,.0f}")
                    st.write(f"**Down Payment ({down_payment_pct}%):** R{down_payment:,.0f}")
                    st.write(f"**Loan Amount:** R{loan_amount:,.0f}")
                    st.write(f"**Interest Rate:** {interest_rate}%")
                    st.write(f"**Loan Term:** {loan_term_years} years")
                    st.write(f"**Monthly Mortgage:** R{monthly_mortgage:,.0f}")
                    
                with col2:
                    st.markdown("**Operating Expenses**")
                    st.write(f"Mortgage Payment: R{monthly_mortgage:,.0f}")
                    st.write(f"**Maintenance ({maintenance_pct}%):** R{monthly_maintenance:,.0f}")
                    st.write(f"**Management ({management_pct}%):** R{monthly_management:,.0f}")
                    st.write(f"**Cleaning:** R{monthly_cleaning:,.0f}")
                    st.write(f"**Utilities:** R{utilities_monthly:,.0f}")
                    st.write(f"**Property Tax:** R{monthly_property_tax:,.0f}")
                    st.write(f"**Insurance:** R{monthly_insurance:,.0f}")
                    st.write(f"Total Monthly Expenses: R{total_monthly_expenses:,.0f}")
                    
                    st.markdown("**Returns**")
                    st.write(f"Monthly Cash Flow: R{monthly_cashflow:,.0f}")
                    st.write(f"**Annual Cash Flow:** R{annual_cashflow:,.0f}")
                    st.write(f"**Cash on Cash Return:** {coc_return:.2f}%")
                    st.write(f"**Cap Rate:** {cap_rate:.2f}%")
                    st.write(f"**ROI:** {roi:.2f}%")
                
                st.divider()
                
                # Cash Flow Chart
                st.markdown("**Monthly Cash Flow Breakdown**")
                
                expenses_breakdown = {
                    'Mortgage': monthly_mortgage,
                    'Maintenance': monthly_maintenance,
                    'Management': monthly_management,
                    'Cleaning': monthly_cleaning,
                    'Utilities': utilities_monthly,
                    'Property Tax': monthly_property_tax,
                    'Insurance': monthly_insurance
                }
                
                fig = go.Figure()
                
                # Revenue bar
                fig.add_trace(go.Bar(
                    name='Revenue',
                    x=['Monthly'],
                    y=[monthly_revenue],
                    marker_color='green',
                    text=[f'R{monthly_revenue:,.0f}'],
                    textposition='outside'
                ))
                
                # Expenses bars
                colors = ['red', 'orange', 'coral', 'lightcoral', 'pink', 'lavender', 'lightblue']
                for idx, (expense_name, amount) in enumerate(expenses_breakdown.items()):
                    fig.add_trace(go.Bar(
                        name=expense_name,
                        x=['Monthly'],
                        y=[-amount],
                        marker_color=colors[idx % len(colors)],
                        text=[f'R{amount:,.0f}'],
                        textposition='inside'
                    ))
                
                # Net cash flow
                fig.add_trace(go.Bar(
                    name='Net Cash Flow',
                    x=['Monthly'],
                    y=[monthly_cashflow],
                    marker_color='blue' if monthly_cashflow > 0 else 'darkred',
                    text=[f'R{monthly_cashflow:,.0f}'],
                    textposition='outside'
                ))
                
                fig.update_layout(
                    barmode='relative',
                    title='Monthly Cash Flow Analysis',
                    yaxis_title='Amount (R)',
                    height=500,
                    showlegend=True
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 5-Year Projection
                st.markdown("**5-Year Financial Projection**")
                
                years = list(range(1, 6))
                projected_revenue = [annual_revenue * (1.03 ** (year-1)) for year in years]  # 3% annual growth
                projected_expenses = [annual_operating_expenses * (1.02 ** (year-1)) for year in years]  # 2% expense growth
                projected_noi = [rev - exp for rev, exp in zip(projected_revenue, projected_expenses)]
                
                fig_projection = go.Figure()
                
                fig_projection.add_trace(go.Scatter(
                    x=years,
                    y=projected_revenue,
                    name='Gross Revenue',
                    mode='lines+markers',
                    line=dict(color='green', width=3)
                ))
                
                fig_projection.add_trace(go.Scatter(
                    x=years,
                    y=projected_expenses,
                    name='Operating Expenses',
                    mode='lines+markers',
                    line=dict(color='red', width=3)
                ))
                
                fig_projection.add_trace(go.Scatter(
                    x=years,
                    y=projected_noi,
                    name='Net Operating Income',
                    mode='lines+markers',
                    line=dict(color='blue', width=3)
                ))
                
                fig_projection.update_layout(
                    title='5-Year Financial Projection (with 3% revenue growth)',
                    xaxis_title='Year',
                    yaxis_title='Amount (R)',
                    height=400
                )
                
                st.plotly_chart(fig_projection, use_container_width=True)
                
                # Investment Insights
                st.markdown("**Investment Insights**")
                
                insights = []
                
                if monthly_cashflow > 0:
                    insights.append(f"+ Positive monthly cash flow of R{monthly_cashflow:,.0f}")
                else:
                    insights.append(f"- Negative monthly cash flow of R{monthly_cashflow:,.0f} - property will cost you money each month")
                
                if coc_return > 10:
                    insights.append(f"+ Strong CoC return of {coc_return:.1f}% (target: >10%)")
                elif coc_return > 5:
                    insights.append(f"~ Moderate CoC return of {coc_return:.1f}% (target: >10%)")
                else:
                    insights.append(f"- Weak CoC return of {coc_return:.1f}% (target: >10%)")
                
                if cap_rate > 6:
                    insights.append(f"+ Good cap rate of {cap_rate:.1f}% (target: >6%)")
                elif cap_rate > 4:
                    insights.append(f"~ Fair cap rate of {cap_rate:.1f}% (target: >6%)")
                else:
                    insights.append(f"- Low cap rate of {cap_rate:.1f}% (target: >6%)")
                
                if occupancy_rate >= 60:
                    insights.append(f"+ Projected {occupancy_rate}% occupancy is realistic for the area")
                else:
                    insights.append(f"~ Projected {occupancy_rate}% occupancy may be conservative")
                
                if is_undervalued:
                    insights.append(f"+ Property is undervalued by R{valuation_diff:,.0f} - potential for appreciation")
                else:
                    insights.append(f"~ Property may be overpriced by R{abs(valuation_diff):,.0f}")
                
                for insight in insights:
                    st.write(insight)

            with tab4:
                st.subheader("Property Summary")
                
                # Create two columns - left for details, right for map
                col_map, col_info = st.columns([1, 1])
                
                with col_map:
                    st.subheader("Location Map")
                    # Create a Google Maps-style map using Folium
                    # Use session state values to reflect latest geocoded address
                    map_lat = st.session_state.latitude
                    map_lng = st.session_state.longitude
                    resolved_addr = st.session_state.get("resolved_address")
                    provider = st.session_state.get("geo_provider")
                    
                    m = folium.Map(
                        location=[map_lat, map_lng],
                        zoom_start=13,
                        tiles="OpenStreetMap"
                    )
                    
                    # Add marker for the property
                    folium.Marker(
                        location=[map_lat, map_lng],
                        popup=(resolved_addr or f"{bedrooms} BR, {bathrooms} BA Property"),
                        tooltip="Property Location",
                        icon=folium.Icon(color='red', icon='info-sign')
                    ).add_to(m)
                    
                    # Use a dynamic key so Streamlit re-renders when coords change
                    map_key = f"map_{map_lat:.5f}_{map_lng:.5f}"
                    st_folium(m, width=500, height=400, key=map_key)
                    st.caption(f"Coordinates: {map_lat:.5f}, {map_lng:.5f}")
                    if resolved_addr:
                        st.caption(f"Resolved: {resolved_addr} ({provider})")
                
                with col_info:
                    st.subheader("Property Details")
                    st.write("**Features:**")
                    st.write(f"• Bedrooms: {bedrooms}")
                    st.write(f"• Bathrooms: {bathrooms}")
                    st.write(f"• Capacity: {accommodates} guests")
                    st.write(f"• Parking: {parking_spaces} spaces")
                    st.write(f"• Size: {square_meters} m²")
                    st.write(f"• Pool: {'Yes' if pool else 'No'}")
                    st.write(f"• Garden: {'Yes' if garden else 'No'}")
                    st.write(f"• Security: {'Yes' if security else 'No'}")
                    st.write(f"• Beach: {'Yes' if near_beach else 'No'}")

            st.divider()
            st.subheader("Assessment")
            if is_undervalued:
                st.success("GOOD VALUE - Consider this property!")
            else:
                st.warning("OVERPRICED - Negotiate or keep looking")

    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.info("Please check your input values")
        import traceback
        st.write(traceback.format_exc())

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")
st.caption("Disclaimer: ML predictions are estimates. Consult real estate professionals for accurate valuations.")
