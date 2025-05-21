import streamlit as st
st.set_page_config(page_title="SolarSaver AI", layout="wide")  # ✅ Must be first Streamlit command

from streamlit_js_eval import streamlit_js_eval
from get_weather_module import get_weather, get_coordinates
from datetime import datetime
import random

# ---- Solar Panel Efficiency Model ----
uk_solar_irradiance = {
    "London": 3.2,
    "Manchester": 2.7,
    "Edinburgh": 2.5,
    "Cardiff": 2.9,
    "Belfast": 2.4,
    "Other": 2.8
}
orientation_factor = {
    "South": 1.0,
    "East": 0.85,
    "West": 0.85,
    "North": 0.5
}

def calculate_output(location, area, eff, orient):
    irradiance = uk_solar_irradiance.get(location, 2.8) * orientation_factor[orient]
    daily_kwh = irradiance * area * (eff / 100)
    annual_savings = daily_kwh * 365 * 0.30
    system_cost = area * 200
    break_even = system_cost / annual_savings if annual_savings > 0 else None
    return daily_kwh, annual_savings, break_even

# ---- UI ----
st.title("🔆 SolarSaver AI Dashboard")
st.caption("Live solar panel performance estimate + location-based weather irradiance data.")

# --- Sidebar Input ---
with st.sidebar:
    st.header("Your Panel Setup")
    location = st.selectbox("Location", list(uk_solar_irradiance.keys()))
    area = st.number_input("Panel area (m²)", 1.0, 100.0, 10.0)
    eff = st.slider("Efficiency (%)", 10, 25, 18)
    orientation = st.selectbox("Panel facing", list(orientation_factor.keys()))
    st.markdown("---")
    st.write("📅 Last updated:", datetime.now().strftime("%d %b %Y"))

st.sidebar.markdown("---")
st.sidebar.header("🔬 Simulation Settings")
sim_type = st.sidebar.selectbox("Simulation time scale", ["1 Day", "1 Week", "1 Month", "1 Year"])
sim_cloud_cover = st.sidebar.slider("Average cloud cover (%)", 0, 100, 30)
sim_temp = st.sidebar.slider("Average temperature (°C)", -10, 45, 20)


# --- Performance Estimate ---
daily_kwh, annual_savings, break_even = calculate_output(location, area, eff, orientation)
st.subheader("⚡ Estimated Solar Panel Performance")
col1, col2 = st.columns(2)
col1.metric("Daily Output (kWh)", f"{daily_kwh:.2f}")
col2.metric("Annual Savings (£)", f"{annual_savings:.2f}")
if break_even:
    st.success(f"💰 Break-even in {break_even:.1f} years")
else:
    st.warning("Check your inputs — savings too low.")

    # --- Solar Output Chart (Simulated by Month) ---
import pandas as pd

# Monthly irradiance multiplier (approximate seasonal variation for UK)
monthly_factors = {
    "Jan": 0.45, "Feb": 0.55, "Mar": 0.75, "Apr": 0.95,
    "May": 1.1, "Jun": 1.15, "Jul": 1.1, "Aug": 1.0,
    "Sep": 0.85, "Oct": 0.65, "Nov": 0.5, "Dec": 0.4
}

# Simulate daily output per month
monthly_output = {
    month: daily_kwh * factor for month, factor in monthly_factors.items()
}

df_output = pd.DataFrame({
    "Month": list(monthly_output.keys()),
    "Estimated Daily Output (kWh)": list(monthly_output.values())
}).set_index("Month")

st.subheader("📊 Monthly Estimated Solar Output")
st.line_chart(df_output)

# --- Yearly Output & Savings Chart ---
monthly_days = {
    "Jan": 31, "Feb": 28, "Mar": 31, "Apr": 30,
    "May": 31, "Jun": 30, "Jul": 31, "Aug": 31,
    "Sep": 30, "Oct": 31, "Nov": 30, "Dec": 31
}

monthly_energy = {month: daily_kwh * factor * monthly_days[month] 
                  for month, factor in monthly_factors.items()}

monthly_savings = {month: output * 0.30 for month, output in monthly_energy.items()}

df_yearly = pd.DataFrame({
    "Month": list(monthly_energy.keys()),
    "Monthly Output (kWh)": list(monthly_energy.values()),
    "Monthly Savings (£)": list(monthly_savings.values())
}).set_index("Month")

st.subheader("📆 Yearly Solar Output & Savings")
st.line_chart(df_yearly)


# --- Optimization Tips ---
st.subheader("💡 Optimization Tips")
if orientation != "South":
    st.info("📍 South-facing panels yield the best sun exposure in the UK.")
if eff < 16:
    st.warning("🔧 Consider upgrading to higher-efficiency panels.")
if daily_kwh < 3:
    st.info("☁️ Consider panel tilt or cleaning to improve yield.")

# --- Weather Section ---
st.markdown("---")
st.subheader("🌍 Weather-Based Solar Irradiance")

weather = None  # ✅ Prevent NameError later

coords = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition")

if coords is None:
    st.info("📡 Waiting for GPS permission...")
elif isinstance(coords, dict) and "coords" in coords:
    lat = coords["coords"]["latitude"]
    lon = coords["coords"]["longitude"]
    st.success(f"📍 GPS-detected: {lat:.2f}, {lon:.2f}")
    weather = get_weather(lat, lon)
else:
    st.warning("⚠️ Could not detect GPS. Use city input below.")

# --- Manual City Fallback ---
city_list = ["London, GB", "Manchester, GB", "Edinburgh, GB", "Cardiff, GB", "Belfast, GB", "Birmingham, GB", "Glasgow, GB"]
city = st.selectbox("Or select your city manually:", city_list)
if st.button("Use Selected City"):
    lat, lon = get_coordinates(city)
    if lat and lon:
        weather = get_weather(lat, lon)
        st.success(f"📍 Coordinates for {city}: {lat:.2f}, {lon:.2f}")
    else:
        st.error("❌ Could not get coordinates for that city.")

# --- Weather Output Display ---
if weather:
    if isinstance(weather, dict) and "error" in weather:
        st.error(weather["error"])
    else:
        st.subheader("🌤️ Current Weather Irradiance")
        st.write(f"**Sky:** {weather.get('description', 'N/A')}")
        st.write(f"**Cloud cover:** {weather.get('clouds', 'N/A')}%")
        st.write(f"**Estimated irradiance:** {weather.get('irradiance_kwh_per_m2', 'N/A')} kWh/m²/day")
        if "tip" in weather:
            st.info(weather["tip"])

import pandas as pd
from datetime import datetime

if weather and "forecast" in weather:
    st.subheader("📊 48-Hour Irradiance Forecast")

    forecast_data = weather["forecast"]
    times = [datetime.fromtimestamp(t[0]).strftime("%d %b %H:%M") for t in forecast_data]
    values = [t[1] for t in forecast_data]

    df_forecast = pd.DataFrame({
        "Time": times,
        "Estimated Irradiance (kWh/m²)": values
    }).set_index("Time")

    st.line_chart(df_forecast)


