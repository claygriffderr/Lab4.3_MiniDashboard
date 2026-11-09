"""Customer Acquisition Dashboard.

Streamlit app for the marketing team: tracks how new vs returning customers
behave in the 2025 e-commerce orders data (data/online_orders.csv).

Sections: load -> sidebar filters -> KPIs -> charts -> insights.
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA_PATH = Path(__file__).parent / "data" / "online_orders.csv"

# Customer-type colors (blue / orange, a colorblind-safe pair).
# Every chart also labels the groups in text, so color is never the only cue.
COLORS = {"New": "#2a78d6", "Returning": "#eb6834"}
TYPE_ORDER = ["New", "Returning"]

st.set_page_config(page_title="Customer Acquisition Dashboard", layout="wide")


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
@st.cache_data
def load_data(path: Path) -> tuple[pd.DataFrame, int]:
    """Read the orders CSV and add helper columns.

    Returns the cleaned data and how many rows were dropped for blank values.
    """
    df = pd.read_csv(path, parse_dates=["order_date"])

    # Blank handling: drop any row with a missing value. The 2025 file has no
    # blanks, so nothing is dropped today, but the count is reported in a caption.
    rows_before = len(df)
    df = df.dropna()
    dropped = rows_before - len(df)

    df["is_new"] = df["customer_type"].eq("New")
    df["is_returned"] = df["returned"].eq("Yes")
    # Month as a timestamp (first of month) so it sorts and plots on a date axis.
    df["month"] = df["order_date"].dt.to_period("M").dt.to_timestamp()
    return df, dropped


df, dropped_rows = load_data(DATA_PATH)


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------
st.sidebar.header("Filters")

months = sorted(df["month"].unique())
month_labels = [pd.Timestamp(m).strftime("%b %Y") for m in months]
start_label, end_label = st.sidebar.select_slider(
    "Date (month range)",
    options=month_labels,
    value=(month_labels[0], month_labels[-1]),
)
start_month = months[month_labels.index(start_label)]
end_month = months[month_labels.index(end_label)]

all_categories = sorted(df["category"].unique())
categories = st.sidebar.multiselect(
    "Product category", all_categories, default=all_categories
)

all_devices = sorted(df["device"].unique())
devices = st.sidebar.multiselect("Device", all_devices, default=all_devices)

metric = st.sidebar.radio(
    "Purchase measure",
    ["Revenue", "Units"],
    help="Sets the measure used in the first KPI and the purchase-size box plot.",
)

filtered = df[
    df["month"].between(start_month, end_month)
    & df["category"].isin(categories)
    & df["device"].isin(devices)
]

st.sidebar.caption(f"Showing {len(filtered):,} of {len(df):,} orders.")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("Customer Acquisition Dashboard")
st.caption(
    "E-commerce orders, 2025 — for marketing planning. "
    f"Data handling: rows with blank values are dropped ({dropped_rows} dropped; "
    "the source file has no blanks). A 'new customer' is one order flagged New, "
    "since the data has no customer IDs."
)

if filtered.empty:
    st.warning(
        "No orders match the current filters. Select at least one product "
        "category and one device, or widen the month range."
    )
    st.stop()


# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
kpi1, kpi2, kpi3 = st.columns(3)

if metric == "Revenue":
    kpi1.metric("Revenue (USD)", f"${filtered['revenue'].sum():,.0f}")
else:
    kpi1.metric("Units sold", f"{filtered['units'].sum():,}")

kpi2.metric(
    "New customers",
    f"{filtered['is_new'].sum():,}",
    help="Number of orders placed by customers flagged New.",
)
kpi3.metric("Average rating", f"{filtered['rating_1to5'].mean():.2f} / 5")
