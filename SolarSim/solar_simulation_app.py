# --- solar_simulation_app.py (Complete Streamlit App with PVGIS, Battery, Load Match, PDF, Feedback, Email) ---
import smtplib
from email.message import EmailMessage
from datetime import datetime
import streamlit as st
import pandas as pd
import numpy as np
import requests
import altair as alt
from fpdf import FPDF
from streamlit_js_eval import streamlit_js_eval
from functools import lru_cache

st.set_page_config(page_title="Solar Simulation App", layout="wide")

# --- Sidebar Inputs ---
st.sidebar.header("Location Settings")
use_live_forecast = st.sidebar.toggle("Use Live PVGIS Forecast", value=True)
location_method = st.sidebar.radio("Get location from", ["GPS", "Manual"])
city = st.sidebar.text_input("City (for info only)", value="London")

st.sidebar.header("Solar Panel")
area = st.sidebar.number_input("Panel Area (m²)", 1.0, 100.0, 10.0)
eff = st.sidebar.slider("Panel Efficiency (%)", 10, 25, 18)
tilt = st.sidebar.slider("Tilt Angle (°)", 0, 90, 30)
orientation = st.sidebar.selectbox("Orientation", ["South", "East", "West", "North"])
system_loss = st.sidebar.slider("System Loss (%)", 0, 30, 14)

st.sidebar.header("Battery")
battery_brand = st.sidebar.selectbox("Battery Brand", ["Tesla Powerwall 2 (13.5 kWh)", "Sonnen Eco (10 kWh)", "LG Chem RESU (9.8 kWh)", "Generic DIY (5 kWh)"])
brand_capacity = {"Tesla Powerwall 2 (13.5 kWh)": 13.5, "Sonnen Eco (10 kWh)": 10.0, "LG Chem RESU (9.8 kWh)": 9.8, "Generic DIY (5 kWh)": 5.0}
battery_size = brand_capacity[battery_brand]
battery_efficiency = 0.9

st.sidebar.header("Load")
base_load = st.sidebar.slider("Base Load (kWh/hr)", 0.1, 5.0, 0.5)
load_file = st.sidebar.file_uploader("Upload Hourly Load (CSV, 1 column)")
user_load = None
if load_file:
    df_load = pd.read_csv(load_file)
    if df_load.shape[1] == 1:
        user_load = df_load.iloc[:, 0].tolist()

st.sidebar.header("Simulation Time")
sim_type = st.sidebar.selectbox("Simulation Duration", ["1 Day", "1 Week"])

orien_to_azimuth = {"South": 0, "East": 90, "West": 270, "North": 180}

# --- Location ---
coords = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition")
if coords and isinstance(coords, dict) and "coords" in coords:
    lat = coords["coords"]["latitude"]
    lon = coords["coords"]["longitude"]
else:
    lat, lon = 51.5072, -0.1276

azimuth = orien_to_azimuth[orientation]

# --- Forecast from PVGIS ---
@lru_cache(maxsize=32)
def get_pvgis_data(lat, lon, tilt, azimuth):
    url = f"https://re.jrc.ec.europa.eu/api/v5_2/seriescalc?lat={lat}&lon={lon}&raddatabase=PVGIS-SARAH&startyear=2016&endyear=2016&outputformat=json&optimalangles=0&angle={tilt}&aspect={azimuth}&pvtechchoice=crystSi&loss={system_loss}"
    r = requests.get(url)
    if r.status_code == 200:
        data = r.json()["outputs"]["hourly"][:48]
        times = [entry["time"] for entry in data]
        irradiance = [entry["G(i)"] / 1000 for entry in data]  # W/m² to kW/m²
        temps = [entry.get("T2m", 0) for entry in data]
        return pd.DataFrame({"Time": times, "Irradiance (kW/m²)": irradiance, "Temp (°C)": temps})
    return pd.DataFrame()

df_forecast = get_pvgis_data(lat, lon, tilt, azimuth) if use_live_forecast else pd.DataFrame()
if df_forecast.empty:
    st.warning("Forecast data unavailable.")
else:
    df_forecast["Time"] = pd.to_datetime(df_forecast["Time"])
    df_forecast.set_index("Time", inplace=True)
    df_forecast["kWh"] = df_forecast["Irradiance (kW/m²)"] * area * (eff / 100)

    battery_state = 0
    stored_kwh = 0
    discharge = 0
    battery_history = []
    hourly_kwh = df_forecast["kWh"].tolist()
    matched_load = user_load if user_load and len(user_load) == len(hourly_kwh) else [base_load] * len(hourly_kwh)
    net_balance = []

    for gen, load in zip(hourly_kwh, matched_load):
        excess = max(0, gen - load)
        shortage = max(0, load - gen)
        charge = min(battery_size - battery_state, excess * battery_efficiency)
        battery_state += charge
        discharge_kwh = min(battery_state, shortage)
        battery_state -= discharge_kwh
        stored_kwh += charge
        discharge += discharge_kwh
        net_balance.append(gen - load)
        battery_history.append(battery_state)

    df_forecast["User Load (kWh)"] = matched_load
    df_forecast["Net Balance (kWh)"] = net_balance
    df_forecast["Battery State (kWh)"] = battery_history

    st.title("Solar Forecast and Battery Analysis")
    st.metric("Total Output", f"{sum(hourly_kwh):.1f} kWh")
    st.metric("Stored in Battery", f"{stored_kwh:.1f} kWh")
    st.metric("Discharged", f"{discharge:.1f} kWh")

    st.line_chart(df_forecast[["kWh", "User Load (kWh)"]])
    st.line_chart(df_forecast["Battery State (kWh)"])

    st.subheader("Export")
    csv = df_forecast.reset_index().to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "forecast.csv", "text/csv")

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Solar Forecast Report", ln=True, align="C")
    for i, row in df_forecast.reset_index().iterrows():
        pdf.cell(200, 8, txt=f"{row['Time']} | {row['kWh']:.2f} kWh | Battery: {row['Battery State (kWh)']:.2f}", ln=True)
        if i >= 30:
            break
    pdf_output = pdf.output(dest='S').encode('latin-1')
    st.download_button("Download PDF", pdf_output, "report.pdf", mime="application/pdf")

# --- Feedback Section ---
st.subheader("Feedback")
with st.form("feedback_form"):
    name = st.text_input("Your Name")
    feedback = st.text_area("Your feedback")
    submitted = st.form_submit_button("Submit")
    if submitted:
        with open("feedback.csv", "a", encoding="utf-8") as f:
            f.write(f"{datetime.now()},{name},{feedback}\n")
        st.success("Thank you for your feedback.")

        try:
            email_address = st.secrets["email_user"]
            email_password = st.secrets["email_pass"]
            msg = EmailMessage()
            msg["Subject"] = "New Feedback"
            msg["From"] = email_address
            msg["To"] = email_address
            msg.set_content(f"{name} said:\n{feedback}")
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(email_address, email_password)
                smtp.send_message(msg)
        except Exception as e:
            st.warning(f"Email error: {e}")