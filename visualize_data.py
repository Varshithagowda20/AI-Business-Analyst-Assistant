import sqlite3
import pandas as pd
import plotly.express as px

# Connect to database
connection = sqlite3.connect("data/business.db")

# Read sales data
df = pd.read_sql_query("SELECT * FROM sales", connection)

# Calculate revenue and profit for each product
product_analysis = (
    df.groupby("product")[["revenue", "profit"]]
    .sum()
    .reset_index()
)

print(product_analysis)

# Create comparison chart
fig = px.bar(
    product_analysis,
    x="product",
    y=["revenue", "profit"],
    barmode="group",
    title="Revenue vs Profit by Product",
    labels={
        "product": "Product",
        "value": "Amount",
        "variable": "Business Metric"
    }
)

# Display chart
fig.show()

connection.close()