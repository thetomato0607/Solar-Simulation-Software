# SolarSim AI – Fast, Accurate Solar Forecasting with Battery Simulation

SolarSim AI is a professional solar simulation tool built for solar installers, SMEs, and developers who need fast, flexible, and accurate performance and ROI forecasting. Powered by real PVGIS irradiance data, it supports location-aware modeling, smart battery logic, and lifestyle-based load estimation without requiring spreadsheets or CSV uploads.

---

## Key Features

### PV Forecasting via PVGIS
- Uses PVGIS SARAH data to simulate realistic hourly solar irradiance
- GPS detection or manual postcode/city input for precise site modeling
- Adjustable panel tilt, orientation, system loss, and efficiency

### Battery Charge and Discharge Simulation
- Models real-time battery usage based on generation and load
- Supports Tesla Powerwall, LG Chem, Sonnen, or custom DIY battery sizes
- Tracks energy stored, discharged, and wasted across the time window

### Load Estimation
- Upload hourly load data via CSV (1-column)
- Fallback to a default base load or connect with AI load predictor (coming soon)

### Performance Visualization
- Hourly plots of solar generation, user load, and battery state
- Instant metrics: total kWh output, stored energy, battery contribution

### Export Options
- Download complete forecast as CSV
- Export a professional PDF summary report with battery breakdown

### Feedback and Notifications
- Built-in feedback form for internal users or client input
- Automatic email notification to admin or installer on submission

---

## Setup

### Local Requirements

```bash
pip install streamlit pandas numpy altair fpdf requests streamlit-js-eval
