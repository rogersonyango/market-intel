# Uganda Market Intelligence

A crop price forecasting and advisory dashboard for Ugandan smallholder farmers. It turns historical market prices (WFP), weather, and a forecasting model into plain sell/hold advice per crop and market — including which market pays best, current demand, and how stale the underlying data is.

**Live app:** _add your Streamlit URL here after deploying_

## What it does

- **Sell signal** — sell now / hold, with a confidence score
- **Best market** — where the same crop currently fetches the highest price, and the gap vs. the selected market
- **Demand level** — low / moderate / high, from a demand index
- **Data-freshness banner** — forecasts are only as good as how current the data is, so the app surfaces the data age up front
- **Charts** — price trend (gap-aware), cross-market comparison, weather (rainfall vs. price), and forecast detail

## Repo structure

```
uganda-market-intel/
├── streamlit_app.py            # dashboard entrypoint
├── requirements.txt
├── .streamlit/config.toml      # theme
├── data/
│   ├── raw/                    # WFP source prices
│   └── processed/              # cleaned data + model outputs (app reads these)
├── notebooks/
│   ├── 01_exploratory_data_analysis.ipynb
│   ├── 02_price_prediction_model.ipynb
│   └── 03_decision_logic.ipynb
└── reports/                    # written report + presentation
```

The dashboard reads only pre-computed outputs (`data/processed/decision_outputs.csv` and `market_data_with_weather.csv`). It does no cleaning or modelling itself — that happens in the notebooks, in order.

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app opens at `http://localhost:8501`.

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub (public).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. **New app** → select this repo, branch `main`, main file `streamlit_app.py`.
4. Deploy. Pushes to `main` auto-redeploy.

## Data

Prices are from the WFP food-prices dataset for Uganda. Forecasts cover a 5-market core (Owino, Iganga, Jinja, Mbarara, Lira) where weather data is available; the market-comparison view includes every market carrying a given crop.

## Notes & limitations

- Forecasts are a decision aid, not a guarantee. The freshness banner flags when the underlying data is old enough that a signal should be treated as a rough guide.
- Where the trained model did not beat a naive baseline for a specific crop/market at its horizon, the app falls back to the baseline and says so in the Forecast Detail tab.
