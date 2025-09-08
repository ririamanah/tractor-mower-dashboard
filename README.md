# 🚜 Tractor & Mower Sales Dashboard (Streamlit)

Interactive dashboard for PLE **Tractor** and **Mower** unit sales.

## ✨ Features
- Load data from bundled Excel (`data/ple_sales.xlsx`) or upload a new file via the sidebar
- Filters: product, region, year (optionally include `World` aggregate)
- KPIs: totals, YoY delta, top region, product mix
- Charts: stacked area by region, product comparison, seasonality heatmap
- Pivot table and CSV download

## 🧩 Project Structure
```
.
├── app.py
├── requirements.txt
├── .streamlit/
│   └── config.toml
└── data/
    └── ple_sales.xlsx   # Provided sample data (from your upload)
```

## 🚀 Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## ☁️ Deploy via GitHub → Streamlit Community Cloud
1. Push this folder to a **public GitHub repo** (e.g., `username/tractor-mower-dashboard`).
2. Go to https://share.streamlit.io/ and click **New app**.
3. Select your repo, set **Main file path** to `app.py`, and deploy.
4. (Optional) To update data, commit a new file to `data/ple_sales.xlsx` or use the **upload** feature in the sidebar at runtime.

> If the app fails to parse headers, double-check your Excel sheets are named **`Mower Unit Sales`** and **`Tractor Unit Sales`** with header row on the second line (as in PLE).

## 🔧 Customization
- To add new regions or rename labels, edit the `REGION_ALIASES` dict in `app.py`.
- To change theme, edit `.streamlit/config.toml`.

---
Made with ❤️ using Streamlit.
