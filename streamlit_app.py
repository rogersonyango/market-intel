"""
app.py -- Farmer Market Intelligence Dashboard
OWNER: ML + Dashboard

PURPOSE
The farmer-facing prototype. Reads only pre-computed outputs from the pipeline --
no cleaning, modeling, or decision logic runs inside this file. Run from the
project folder with:
    streamlit run streamlit_app.py

INPUT (place these two files next to app.py, or adjust DATA_DIR below)
    decision_outputs.csv        (from decision_logic_v2.ipynb)
    market_data_with_weather.csv (from the cleaning + weather notebook)

LAYOUT
    Sidebar: crop selector, market selector
    Main:
        - Data-freshness banner (uses data_age_months, since forecasts are only
          as good as how current the underlying data is -- see decision_logic.ipynb)
        - Action panel: sell signal, best market + gap, demand badge, anomaly alert
        - Tabs: Price Trend | Market Comparison | Weather | Forecast Detail
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "processed"

st.set_page_config(page_title="Farmer Market Intelligence", layout="wide", page_icon="\U0001F33E")


@st.cache_data
def load_data():
    decisions = pd.read_csv(DATA_DIR / "decision_outputs.csv", parse_dates=["as_of_date", "target_date"])
    wide = pd.read_csv(DATA_DIR / "market_data_with_weather.csv", parse_dates=["date"])
    return decisions, wide


def reindex_monthly(g):
    """Reindex a single market-crop price series to a continuous monthly calendar,
    so real reporting gaps show as breaks in the chart instead of being silently
    bridged into a misleading straight line."""
    g = g.set_index("date").sort_index()
    full_range = pd.date_range(g.index.min(), g.index.max(), freq="MS") + pd.DateOffset(days=14)
    return g.reindex(full_range)


try:
    decisions, wide = load_data()
except FileNotFoundError as e:
    st.error(
        "Could not find the required data files. Place `decision_outputs.csv` and "
        "`market_data_with_weather.csv` in the same folder as this app.\n\n"
        f"Details: {e}"
    )
    st.stop()

st.title("\U0001F33E Farmer Market Intelligence")
st.caption("Price, demand and weather insights for Uganda's staple crop markets")

st.sidebar.header("Select crop & market")
crop = st.sidebar.selectbox("Crop", sorted(decisions["commodity"].unique()))
market = st.sidebar.selectbox("Market", sorted(decisions["market"].unique()))

row_df = decisions[(decisions["commodity"] == crop) & (decisions["market"] == market)]

if row_df.empty:
    st.warning("No decision data available for this crop/market combination yet.")
else:
    row = row_df.iloc[0]

    # --- Data freshness banner ---
    age = row["data_age_months"]
    if age >= 9:
        st.warning(
            f"\u26A0\uFE0F Underlying data for {market} - {crop} is **{age} months old**. "
            "Forecasts at this range are real but noticeably less precise -- treat this "
            "signal as a rough guide, not a confident prediction."
        )
    elif age >= 5:
        st.info(f"\u2139\uFE0F Data for {market} - {crop} is {age} months old as of the last update.")

    # --- Action panel ---
    col1, col2, col3, col4 = st.columns(4)

    signal_labels = {
        "sell_now": ("\U0001F7E2", "Sell Now"),
        "wait": ("\U0001F7E1", "Wait"),
        "hold": ("\U0001F535", "Hold"),
        "insufficient_data": ("\u26AA", "No Signal"),
    }
    emoji, label = signal_labels.get(row["sell_signal"], ("", row["sell_signal"]))
    col1.metric("Sell Signal", f"{emoji} {label}", f"{row['sell_confidence']*100:.0f}% confidence")
    col2.metric("Best Market", row["best_market"], f"{row['price_gap_pct']:+.1f}% vs. here")
    col3.metric("Demand", row["demand_level"].title())
    col4.metric("Anomaly", "\u26A0\uFE0F Yes" if row["anomaly_flag"] else "None")

    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(
        ["\U0001F4C8 Price Trend", "\U0001F5FA\uFE0F Market Comparison", "\U0001F327\uFE0F Weather", "\U0001F52E Forecast Detail"]
    )

    # --- Tab 1: Price trend (gap-aware) ---
    with tab1:
        series = wide[(wide["commodity"] == crop) & (wide["market"] == market)]
        if series.empty:
            st.info("No price history available for this combination.")
        else:
            series_monthly = reindex_monthly(series).reset_index().rename(columns={"index": "date"})
            fig = px.line(series_monthly, x="date", y="price", markers=True,
                          title=f"{crop} price over time -- {market}")
            fig.update_layout(yaxis_title="Price (UGX)", xaxis_title="")
            st.plotly_chart(fig, width="stretch")
            st.caption("Gaps in the line reflect genuine reporting gaps in the data, not missing chart points.")

    # --- Tab 2: Market comparison (wide dataset -- all markets, not just the core) ---
    with tab2:
        crop_data = wide[wide["commodity"] == crop]
        if crop_data.empty:
            st.info("No market comparison data available for this crop.")
        else:
            latest_date = crop_data["date"].max()
            comparison = (
                crop_data[crop_data["date"] == latest_date][["market", "price"]]
                .sort_values("price", ascending=False)
            )
            fig = px.bar(comparison, x="market", y="price",
                        title=f"{crop} price by market -- {latest_date.date()}")
            fig.update_layout(xaxis_title="", yaxis_title="Price (UGX)", xaxis_tickangle=-45)
            st.plotly_chart(fig, width="stretch")
            st.caption("Includes every market carrying this crop, not just the 5-market forecasting core.")

    # --- Tab 3: Weather (core markets only -- weather isn't pulled elsewhere) ---
    # Two separate stacked charts, not a dual-axis chart. A dual-axis chart lets each
    # series' scale be chosen independently, which can visually imply a relationship
    # (or hide one) that isn't really there. Two charts sharing only the x-axis let
    # the reader compare honestly without that distortion.
    with tab3:
        core_series = wide[(wide["commodity"] == crop) & (wide["market"] == market) & (wide["forecastable"])]
        if core_series.empty:
            st.info(
                "Weather data is only available for the 5-market forecasting core "
                "(Owino, Iganga, Jinja, Mbarara, Lira). This market/crop pair isn't in that set."
            )
        else:
            core_monthly = reindex_monthly(core_series).reset_index().rename(columns={"index": "date"})

            fig_price = px.line(core_monthly, x="date", y="price", markers=True,
                                title=f"{crop} price \u2014 {market}")
            fig_price.update_layout(yaxis_title="Price (UGX)", xaxis_title="")
            st.plotly_chart(fig_price, width="stretch")

            fig_rain = px.bar(core_monthly, x="date", y="rainfall_mm",
                              title=f"Rainfall \u2014 {market}")
            fig_rain.update_layout(yaxis_title="Rainfall (mm)", xaxis_title="Date")
            st.plotly_chart(fig_rain, width="stretch")

    # --- Tab 4: Forecast detail ---
    with tab4:
        c1, c2 = st.columns(2)
        with c1:
            st.write(f"**Last record date:** {row['as_of_date'].date()}")
            st.write(f"**Target date:** {row['target_date'].date()}")
            st.write(f"**Data gap:** {row['data_age_months']} months")
        with c2:
            st.write(f"**Last record price:** {row['current_price']:.0f} UGX")
            st.write(f"**Forecast price:** {row['forecast_price']:.0f} UGX")
            st.write(f"**Source:** {row['forecast_source']}")

        if row["forecast_source"] == "model":
            st.success(
                "This forecast uses the trained model (XGBoost), which tested more accurate "
                "than the naive baseline for this specific market-crop pair at its current horizon."
            )
        else:
            st.info(
                "This forecast uses a naive baseline (assumes little change from the current "
                "price), since the model did not outperform it for this specific pair at this horizon."
            )

        st.divider()
        st.write("**Demand detail**")
        d1, d2 = st.columns(2)
        d1.write(f"**Demand level:** {row['demand_level'].title()}")
        d2.write(f"**Demand index:** {row['demand_index']:.4f}")
        