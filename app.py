\
import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

st.set_page_config(page_title="Tractor & Mower Sales Dashboard", page_icon="🚜", layout="wide")

# --------------- Helpers ---------------
REGION_ALIASES = {
    "SA": "South America",
    "Eur": "Europe",
    "Europe": "Europe",
    "Pacific": "Pacific",
    "China": "China",
    "World": "World"
}

def _clean_sheet(df_raw: pd.DataFrame, product: str) -> pd.DataFrame:
    """
    Clean a 'Mower Unit Sales' or 'Tractor Unit Sales' sheet exported like the PLE dataset.
    Assumes header row is on index 1, data starts on index 2.
    """
    # Drop all-empty columns
    df = df_raw.dropna(axis=1, how="all").copy()
    # Use second row as header (index 1)
    header_row_idx = 1
    new_cols = df.iloc[header_row_idx].tolist()
    df.columns = new_cols
    df = df.iloc[header_row_idx + 1:].reset_index(drop=True)

    # Coerce Month and numeric columns
    # Some exports name the first column 'Month' or carry a timestamp string
    if "Month" not in df.columns:
        # Fallback: first column
        df.rename(columns={df.columns[0]: "Month"}, inplace=True)

    df["Month"] = pd.to_datetime(df["Month"], errors="coerce")
    # Standardize region names
    df = df.rename(columns=REGION_ALIASES)

    # Keep only expected numeric columns
    keep_cols = ["Month"] + [c for c in df.columns if c in {"South America", "Europe", "Pacific", "China", "World"}]
    df = df[keep_cols]

    # Convert numerics
    for c in keep_cols:
        if c != "Month":
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Melt to long format
    long_df = df.melt(id_vars="Month", var_name="Region", value_name="Units")
    long_df["Product"] = product
    long_df["Year"] = long_df["Month"].dt.year
    long_df["MonthName"] = long_df["Month"].dt.strftime("%b")
    long_df = long_df.dropna(subset=["Units"])
    return long_df

@st.cache_data(show_spinner=False)
def load_data(default_path: Path | None) -> pd.DataFrame:
    if default_path and default_path.exists():
        xls = pd.ExcelFile(default_path)
        mower_raw = pd.read_excel(xls, sheet_name="Mower Unit Sales")
        tractor_raw = pd.read_excel(xls, sheet_name="Tractor Unit Sales")
    else:
        raise FileNotFoundError("Excel file not found. Please upload the dataset.")

    mower = _clean_sheet(mower_raw, "Mower")
    tractor = _clean_sheet(tractor_raw, "Tractor")
    return pd.concat([mower, tractor], ignore_index=True).sort_values("Month")

def kpi_card(label: str, value: float, help_text: str | None = None, delta: float | None = None):
    st.metric(label, f"{int(value):,}", delta=None if delta is None else f"{delta:+,}", help=help_text)

# --------------- Sidebar ---------------
st.sidebar.title("⚙️ Controls")

uploaded = st.sidebar.file_uploader("Upload PLE Excel (optional)", type=["xlsx", "xls"])
default_path = Path("data/ple_sales.xlsx")

if uploaded is not None:
    # Save the uploaded file to a tmp path inside Streamlit's runtime
    tmp_path = Path(st.secrets.get("_tmp_dir", ".")) / "uploaded.xlsx"
    with open(tmp_path, "wb") as f:
        f.write(uploaded.getbuffer())
    data = load_data(tmp_path)
else:
    # Use repo-bundled data by default
    data = load_data(default_path)

# Sidebar filters
products = st.sidebar.multiselect("Product", ["Tractor", "Mower"], default=["Tractor", "Mower"])
regions = st.sidebar.multiselect("Region", sorted(data["Region"].unique()), default=sorted(r for r in data["Region"].unique() if r != "World"))
years = st.sidebar.multiselect("Year", sorted(data["Year"].unique()), default=sorted(data["Year"].unique()))

show_world = st.sidebar.checkbox("Include 'World' aggregate", value=False)

# Apply filters
df = data.copy()
if not show_world:
    df = df[df["Region"] != "World"]
if products:
    df = df[df["Product"].isin(products)]
if regions:
    df = df[df["Region"].isin(regions)]
if years:
    df = df[df["Year"].isin(years)]

# --------------- Header ---------------
st.title("🚜 Tractor & Mower Sales Dashboard")
st.caption("Interactive analytics built with Streamlit. Data source: PLE Dataset (Mower & Tractor Unit Sales).")

# --------------- Top KPIs ---------------
col1, col2, col3, col4 = st.columns(4)
total_units = int(df["Units"].sum())
last_year = max(df["Year"]) if not df.empty else None
prev_year = last_year - 1 if last_year else None

if last_year and prev_year in df["Year"].unique():
    ly_units = int(df[df["Year"] == last_year]["Units"].sum())
    py_units = int(df[df["Year"] == prev_year]["Units"].sum())
    yoy = ly_units - py_units
else:
    ly_units, py_units, yoy = None, None, None

with col1:
    kpi_card("Total Units (Filtered)", total_units, help_text="Sum across filters")
with col2:
    kpi_card(f"Units {last_year}" if last_year else "Units (Latest Year)", 0 if ly_units is None else ly_units, delta=None if yoy is None else yoy)
with col3:
    # Best region by units
    if not df.empty:
        best_region = df.groupby("Region")["Units"].sum().sort_values(ascending=False).index[0]
        best_val = int(df.groupby("Region")["Units"].sum().max())
        st.metric("Top Region", f"{best_region}", help="Highest total units in current filters")
    else:
        st.metric("Top Region", "—")
with col4:
    # Product mix
    if not df.empty:
        mix = df.groupby("Product")["Units"].sum()
        tractor_share = (mix.get("Tractor", 0) / mix.sum() * 100) if mix.sum() else 0
        st.metric("Tractor Share (%)", f"{tractor_share:.1f}%")
    else:
        st.metric("Tractor Share (%)", "—")

st.divider()

# --------------- Charts ---------------
import altair as alt

if df.empty:
    st.info("No data for the selected filters. Try expanding your selections.")
else:
    # Time series by product (stacked by region)
    ts = (df.groupby(["Month", "Product", "Region"], as_index=False)["Units"].sum())

    chart = alt.Chart(ts).mark_area(opacity=0.7).encode(
        x=alt.X("Month:T", title="Month"),
        y=alt.Y("sum(Units):Q", title="Units"),
        color=alt.Color("Region:N", legend=alt.Legend(title="Region")),
        tooltip=["Month:T", "Product:N", "Region:N", alt.Tooltip("sum(Units):Q", title="Units")]
    ).properties(height=320)

    tabs = st.tabs(["📈 Trend by Region (Stacked Area)", "🔁 Product Comparison", "🧭 Seasonality Heatmap", "📊 Pivot Table & Download"])

    with tabs[0]:
        st.subheader("Trend by Region (stacked)")
        for prod in sorted(df["Product"].unique()):
            st.markdown(f"**{prod}**")
            st.altair_chart(chart.transform_filter(alt.datum.Product == prod), use_container_width=True)

    with tabs[1]:
        st.subheader("Product Comparison Over Time")
        comp = (df.groupby(["Month", "Product"], as_index=False)["Units"].sum())
        line = alt.Chart(comp).mark_line(point=True).encode(
            x="Month:T",
            y=alt.Y("Units:Q", title="Units"),
            color="Product:N",
            tooltip=["Month:T", "Product:N", "Units:Q"]
        ).properties(height=320)
        st.altair_chart(line, use_container_width=True)

    with tabs[2]:
        st.subheader("Seasonality Heatmap (Avg Units)")
        sea = (df.assign(MonthNum=lambda d: d["Month"].dt.month)
                 .groupby(["Year", "MonthNum", "Product"], as_index=False)["Units"].mean())
        heat = alt.Chart(sea).mark_rect().encode(
            x=alt.X("MonthNum:O", title="Month"),
            y=alt.Y("Year:O", title="Year"),
            color=alt.Color("Units:Q", title="Avg Units"),
            facet=alt.Facet("Product:N", columns=2),
            tooltip=["Year:O", "MonthNum:O", "Product:N", "Units:Q"]
        ).properties(height=180)
        st.altair_chart(heat, use_container_width=True)

    with tabs[3]:
        st.subheader("Pivot Table")
        piv = pd.pivot_table(df, index=["Year", "MonthName"], columns=["Product", "Region"], values="Units", aggfunc="sum").fillna(0)
        st.dataframe(piv, use_container_width=True)
        st.download_button("⬇️ Download filtered data (CSV)", df.to_csv(index=False).encode("utf-8"), file_name="filtered_sales.csv", mime="text/csv")

# --------------- Footer ---------------
with st.expander("ℹ️ About"):
    st.markdown(
        """
        **Dataset**: PLE (Mower & Tractor Unit Sales).  
        **Notes**: This app supports uploading a newer version of the Excel file via the sidebar.
        """
    )
