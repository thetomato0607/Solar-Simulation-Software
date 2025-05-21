# --- solar_simulation_app.py (full rewritten app) ---
import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime
from streamlit_js_eval import streamlit_js_eval
import requests
import altair as alt
from fpdf import FPDF

# --- Config ---
st.set_page_config(page_title="Solar Simulation", layout="wide")

# --- Sidebar Layout ---
st.sidebar.title("🔧 Simulation Settings")

# Section 1: Location
st.sidebar.subheader("📍 Location & Forecast")
location_method = st.sidebar.radio("Location Source", ["Auto (GPS)", "Manual Entry"])
city = "London"
if location_method == "Manual Entry":
    city = st.sidebar.text_input("City or Postcode (UK)", value="London")
use_live_forecast = st.sidebar.toggle("🌦 Use Live Weather Forecast", value=True)

# Section 2: Solar Panel System
st.sidebar.subheader("🔋 Solar Panel System")
area = st.sidebar.number_input("Panel Area (m²)", 1.0, 100.0, 10.0)
eff = st.sidebar.slider("Panel Efficiency (%)", 10, 25, 18)
tilt = st.sidebar.slider("Tilt Angle (°)", 0, 90, 30)
orientation = st.sidebar.selectbox("Orientation", ["South", "East", "West", "North"])
system_loss = st.sidebar.slider("System Losses (%)", 0, 20, 14)

# Section 3: Environmental
st.sidebar.subheader("🌤 Environmental Conditions")
cloud_cover = st.sidebar.slider("Average Cloud Cover (%)", 0, 100, 30)
temp = st.sidebar.slider("Average Temperature (°C)", -10, 45, 20)

# Section 4: Battery
st.sidebar.subheader("🔋 Battery Storage")
battery_brand = st.sidebar.selectbox("Battery Brand", [
    "Tesla Powerwall 2 (13.5 kWh)",
    "Sonnen Eco (10 kWh)",
    "LG Chem RESU (9.8 kWh)",
    "Generic DIY (5 kWh)"
])
brand_capacity = {
    "Tesla Powerwall 2 (13.5 kWh)": 13.5,
    "Sonnen Eco (10 kWh)": 10.0,
    "LG Chem RESU (9.8 kWh)": 9.8,
    "Generic DIY (5 kWh)": 5.0
}
battery_size = brand_capacity[battery_brand]
battery_efficiency = 0.9

# Section 5: Load
st.sidebar.subheader("⚡️ Energy Use")
base_load = st.sidebar.slider("Base Load (kWh/hour)", 0.0, 5.0, 0.5)

# Section 6: Simulation
st.sidebar.subheader("📅 Simulation Duration")
sim_type = st.sidebar.selectbox("Time Range", ["1 Day", "1 Week", "1 Month", "1 Year"])

# --- Data and Constants ---
orientation_factor = {"South": 1.0, "East": 0.85, "West": 0.85, "North": 0.5}
monthly_factors = {
    "Jan": 0.45, "Feb": 0.55, "Mar": 0.75, "Apr": 0.95,
    "May": 1.1, "Jun": 1.15, "Jul": 1.1, "Aug": 1.0,
    "Sep": 0.85, "Oct": 0.65, "Nov": 0.5, "Dec": 0.4
}

def get_forecast(lat, lon, api_key, hours=48):
    url = f"https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude=current,minutely,daily,alerts&appid={api_key}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json().get("hourly", [])[:hours]
        return [(entry["dt"], entry.get("uvi", 0) * 0.12, entry["weather"][0]["description"], entry.get("clouds", 0)) for entry in data]
    return []

def simulate_output(base_daily_kwh, sim_type, cloud_cover=30, temp=20, use_forecast=None):
    cloud_factor = 1 - (cloud_cover / 100) * 0.9
    temp_factor = 1 - max(0, temp - 25) * 0.003
    corrected_kwh = base_daily_kwh * cloud_factor * temp_factor

    if sim_type in ["1 Day", "1 Week"] and use_forecast:
        times = [datetime.fromtimestamp(t[0]) for t in use_forecast]
        irr_values = [t[1] for t in use_forecast]
        descriptions = [t[2].capitalize() for t in use_forecast]
        clouds = [t[3] for t in use_forecast]
        output = [irr * area * (eff / 100) * (1 - system_loss / 100) * np.cos(np.radians(tilt - 35)) for irr in irr_values]
        return pd.DataFrame({"Time": times, "kWh": output, "Description": descriptions, "Clouds (%)": clouds}).set_index("Time")

    elif sim_type == "1 Month":
        days = np.arange(30)
        variation = 0.85 + 0.15 * np.sin(2 * np.pi * days / 30)
        return pd.DataFrame({"Day": [f"Day {i+1}" for i in range(30)], "Simulated Output (kWh)": corrected_kwh * variation}).set_index("Day")

    elif sim_type == "1 Year":
        return pd.DataFrame({"Month": list(monthly_factors.keys()), "Simulated Output (kWh)": [corrected_kwh * f * 30 for f in monthly_factors.values()]}).set_index("Month")

    return pd.DataFrame({"Simulated Output (kWh)": [corrected_kwh]})

# --- Main App ---
st.title("🧪 Solar Output Simulation")
tilt_corr = np.cos(np.radians(tilt - 35))
irr = 3.0 * orientation_factor[orientation] * tilt_corr
base_daily_kwh = irr * area * (eff / 100) * (1 - system_loss / 100)

coords = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition")
if coords and isinstance(coords, dict) and "coords" in coords:
    lat = coords["coords"]["latitude"]
    lon = coords["coords"]["longitude"]
    st.success(f"📍 GPS-detected location: {lat:.2f}, {lon:.2f}")
else:
    lat, lon = 51.5072, -0.1276
    st.info("🌍 Using default location: London")

api_key = st.secrets.get("openweather_api_key", "YOUR_API_KEY")
hours = 24 if sim_type == "1 Day" else 48 if sim_type == "1 Week" else 0
forecast_data = get_forecast(lat, lon, api_key, hours=hours) if hours and use_live_forecast else None

df_forecast = simulate_output(base_daily_kwh, sim_type, cloud_cover, temp, use_forecast=forecast_data)
df_historical = simulate_output(base_daily_kwh, sim_type, cloud_cover, temp, use_forecast=None)

st.subheader("📊 Output vs Cloud Cover")
if "kWh" in df_forecast:
    chart = alt.Chart(df_forecast.reset_index()).transform_fold(["kWh", "Clouds (%)"]).mark_line().encode(
        x="Time:T", y=alt.Y("value:Q", title="Value"), color="key:N", tooltip=["Time:T", "kWh", "Clouds (%)", "Description"]
    ).properties(height=400)
    st.altair_chart(chart, use_container_width=True)
else:
    st.line_chart(df_historical.iloc[:, 0])

total_kwh = df_forecast["kWh"].sum() if "kWh" in df_forecast else df_historical.iloc[:, 0].sum()
battery_state = 0
stored_kwh = 0
if sim_type in ["1 Day", "1 Week"] and "kWh" in df_forecast:
    for kwh in df_forecast["kWh"]:
        excess = max(0, kwh - base_load)
        charge = min(battery_size - battery_state, excess * battery_efficiency)
        battery_state += charge
        stored_kwh += charge
else:
    stored_kwh = min(total_kwh, battery_size) * battery_efficiency

# --- Metrics ---
st.metric("🔋 Total Energy", f"{total_kwh:.1f} kWh")
st.metric("🔋 Stored in Battery", f"{stored_kwh:.1f} kWh")
st.metric("💰 Estimated Savings", f"£{total_kwh * 0.30:.2f}")
roi_years = (battery_size * 1000) / (stored_kwh * 0.30) if stored_kwh > 0 else None
if roi_years and roi_years < 25:
    st.success(f"📈 Battery ROI: {roi_years:.1f} years")
elif roi_years:
    st.warning(f"⏳ Payback exceeds battery life (~{roi_years:.1f} years)")

# --- PDF Report ---
if "Description" in df_forecast.columns:
    st.subheader("🌤️ Forecast Descriptions")
    st.dataframe(df_forecast[["Description", "Clouds (%)"]])

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Solar Forecast Report", ln=True, align="C")
    pdf.cell(200, 10, txt=f"Location: {lat:.2f}, {lon:.2f}", ln=True)
    pdf.cell(200, 10, txt=f"Simulation Type: {sim_type}", ln=True)
    pdf.cell(200, 10, txt=f"Total Output: {total_kwh:.2f} kWh", ln=True)
    pdf.cell(200, 10, txt=f"Battery: {battery_brand} - Stored: {stored_kwh:.2f} kWh", ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    for i, row in df_forecast.reset_index().iterrows():
        time_str = str(row[0])[:19]
        pdf.cell(200, 8, txt=f"{time_str} - {row['kWh']:.2f} kWh | Clouds: {row['Clouds (%)']}%", ln=True)
        if i > 30:
            break
    pdf_out = pdf.output(dest='S').encode('latin-1')
    st.download_button("📄 Download Forecast PDF", pdf_out, "solar_forecast_report.pdf", mime="application/pdf")

# --- CSV Export ---
if not df_forecast.empty:
    csv = df_forecast.reset_index().to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Forecast CSV", csv, "forecast_output.csv", "text/csv")

# Feedback from users
st.subheader("🗣️ Give Feedback")

with st.form("feedback_form"):
    name = st.text_input("Your Name (optional)")
    feedback = st.text_area("What do you think about the simulation app?")
    submitted = st.form_submit_button("Submit")

    if submitted:
        st.success("Thank you for your feedback!")
        # Optionally save to CSV
        with open("feedback.csv", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()},{name},{feedback.replace(',', ' ')}\n")
