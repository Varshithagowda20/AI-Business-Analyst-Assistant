import sqlite3
import pandas as pd

# Connect to database
connection = sqlite3.connect("data/business.db")

# Load sales data
df = pd.read_sql_query("SELECT * FROM sales", connection)

# Convert order_date into date format
df["order_date"] = pd.to_datetime(df["order_date"])

# Extract month from order date
df["month"] = df["order_date"].dt.month_name()

# Calculate monthly revenue
monthly_revenue = df.groupby("month")["revenue"].sum()

print("Monthly Revenue:")
print(monthly_revenue)

# Find the highest revenue month
best_month = monthly_revenue.idxmax()

print("Highest Revenue Month:", best_month)

connection.close()