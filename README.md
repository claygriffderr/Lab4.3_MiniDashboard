# Customer Acquisition Dashboard

Streamlit dashboard that helps a marketing team track new vs returning customers in
2025 e-commerce orders (`data/online_orders.csv`).

## Run locally

```bash
conda activate dataviz
pip install -r requirements.txt   # if needed
streamlit run app.py
```

## What it shows

- **Sidebar filters:** month range, product category, device, and a Revenue/Units
  switch for the first KPI and the purchase-size box plot.
- **KPIs:** revenue (or units sold), new-customer orders, average rating.
- **Charts:** monthly new-customer share (line), return rate by customer type (bar),
  revenue or units per order by customer type (box plot), new-customer share by
  region (bar).
- **Key insights:** fixed takeaways from the full 2025 data.

## Deploy

On [Streamlit Community Cloud](https://share.streamlit.io), create an app from this
repo, branch `main`, main file `app.py`.
