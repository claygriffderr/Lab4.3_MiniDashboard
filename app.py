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


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------
def style_figure(fig: go.Figure, height: int = 380) -> go.Figure:
    """Shared layout: readable fonts, light grid, no chart-level legend."""
    fig.update_layout(
        height=height,
        font=dict(size=14),
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        hoverlabel=dict(font_size=14),
    )
    return fig


def new_share_over_time(data: pd.DataFrame) -> go.Figure:
    """Line chart: % of orders from new customers, by month."""
    monthly = (
        data.groupby("month")
        .agg(new_orders=("is_new", "sum"), orders=("is_new", "size"))
        .reset_index()
    )
    monthly["pct_new"] = monthly["new_orders"] / monthly["orders"] * 100
    overall = data["is_new"].mean() * 100

    fig = go.Figure(
        go.Scatter(
            x=monthly["month"],
            y=monthly["pct_new"],
            mode="lines+markers",
            line=dict(color=COLORS["New"], width=2),
            marker=dict(size=9),
            customdata=monthly[["new_orders", "orders"]],
            hovertemplate=(
                "%{x|%B %Y}<br>New customers: %{y:.1f}%"
                "<br>%{customdata[0]:,} of %{customdata[1]:,} orders<extra></extra>"
            ),
        )
    )
    # Dashed reference line so months above/below the period average stand out.
    fig.add_hline(
        y=overall,
        line=dict(color="gray", dash="dash", width=1),
        annotation_text=f"Average {overall:.1f}%",
        annotation_position="top left",
    )
    fig.update_xaxes(title="Month", dtick="M1", tickformat="%b")
    fig.update_yaxes(title="New-customer share of orders (%)", ticksuffix="%")
    return style_figure(fig)


def return_rate_by_type(data: pd.DataFrame) -> go.Figure:
    """Bar chart: % of orders returned, New vs Returning."""
    rates = (
        data.groupby("customer_type")
        .agg(returned=("is_returned", "sum"), orders=("is_returned", "size"))
        .reindex(TYPE_ORDER)
        .dropna()  # a filter can leave only one customer type
        .reset_index()
    )
    rates["rate"] = rates["returned"] / rates["orders"] * 100

    fig = go.Figure(
        go.Bar(
            x=rates["customer_type"],
            y=rates["rate"],
            marker_color=[COLORS[t] for t in rates["customer_type"]],
            text=[f"{r:.1f}%" for r in rates["rate"]],
            textposition="outside",
            customdata=rates[["returned", "orders"]],
            hovertemplate=(
                "%{x} customers<br>Return rate: %{y:.1f}%"
                "<br>%{customdata[0]:,.0f} of %{customdata[1]:,.0f} orders returned"
                "<extra></extra>"
            ),
        )
    )
    fig.update_xaxes(title="Customer type")
    # Headroom above the tallest bar so the outside labels are not clipped.
    fig.update_yaxes(
        title="Return rate (% of orders)",
        ticksuffix="%",
        range=[0, max(rates["rate"].max() * 1.25, 1)],
    )
    return style_figure(fig)


def purchase_size_by_type(data: pd.DataFrame, measure: str) -> go.Figure:
    """Box plot: revenue or units per order, New vs Returning."""
    column = "revenue" if measure == "Revenue" else "units"
    fig = px.box(
        data,
        x="customer_type",
        y=column,
        color="customer_type",
        category_orders={"customer_type": TYPE_ORDER},
        color_discrete_map=COLORS,
    )
    # boxmean adds a dashed line for the mean alongside the median.
    fig.update_traces(boxmean=True)
    fig.update_xaxes(title="Customer type")
    if measure == "Revenue":
        fig.update_yaxes(title="Revenue per order (USD)", tickprefix="$")
    else:
        fig.update_yaxes(title="Units per order", dtick=1)
    return style_figure(fig)


def new_share_by_region(data: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart: % of orders from new customers, by region."""
    regions = (
        data.groupby("region")
        .agg(new_orders=("is_new", "sum"), orders=("is_new", "size"))
        .reset_index()
    )
    regions["pct_new"] = regions["new_orders"] / regions["orders"] * 100
    # Ascending sort puts the highest region at the top of a horizontal chart.
    regions = regions.sort_values("pct_new")
    overall = data["is_new"].mean() * 100

    fig = go.Figure(
        go.Bar(
            x=regions["pct_new"],
            y=regions["region"],
            orientation="h",
            marker_color=COLORS["New"],
            text=[f"{p:.1f}%" for p in regions["pct_new"]],
            textposition="outside",
            customdata=regions[["new_orders", "orders"]],
            hovertemplate=(
                "%{y}<br>New customers: %{x:.1f}%"
                "<br>%{customdata[0]:,} of %{customdata[1]:,} orders<extra></extra>"
            ),
        )
    )
    fig.add_vline(
        x=overall,
        line=dict(color="gray", dash="dash", width=1),
        annotation_text=f"All regions {overall:.1f}%",
        annotation_position="top",
    )
    fig.update_xaxes(
        title="New-customer share of orders (%)",
        ticksuffix="%",
        range=[0, max(regions["pct_new"].max() * 1.2, 1)],
    )
    fig.update_yaxes(title="Region")
    return style_figure(fig, height=340)


# Row 1: line chart (full width)
st.subheader("Proportion of new customers over time")
st.plotly_chart(
    new_share_over_time(filtered),
    alt="Line chart of the monthly percentage of orders placed by new customers.",
)
st.caption(
    "Line: share of each month's orders placed by new customers (%). "
    "Dashed line marks the average for the selected period. Hover for order counts; "
    "drag to zoom, double-click to reset."
)

# Row 2: returns bar + purchase-size box plot
left, right = st.columns(2)
with left:
    st.subheader("Return rate by customer type")
    st.plotly_chart(
        return_rate_by_type(filtered),
        alt="Bar chart comparing the percentage of orders returned by new and returning customers.",
    )
    st.caption(
        "Bars: percentage of orders returned for New (blue) and Returning (orange) "
        "customers, with the rate printed above each bar. Hover for counts."
    )
with right:
    unit_label = "revenue (USD)" if metric == "Revenue" else "units"
    st.subheader(f"Purchase size by customer type: {metric.lower()}")
    st.plotly_chart(
        purchase_size_by_type(filtered, metric),
        alt=f"Box plot of {unit_label} per order for new and returning customers.",
    )
    st.caption(
        f"Box plot: {unit_label} per order. The box spans the middle 50% of orders, "
        "the solid line is the median and the dashed line is the mean. "
        "Switch between revenue and units in the sidebar."
    )

# Row 3: region bar chart (replaces the wireframe's map)
st.subheader("Proportion of new customers by region")
st.plotly_chart(
    new_share_by_region(filtered),
    alt="Horizontal bar chart of the percentage of orders from new customers in each region, sorted highest to lowest.",
)
st.caption(
    "Bars: share of each region's orders placed by new customers (%), sorted from "
    "highest (top) to lowest. Dashed line marks all regions combined."
)
