
import pandas as pd

# Read sales data
df = pd.read_csv("data/sales_data.csv")

# Display first 5 records
print(df.head())

# Calculate total revenue
total_revenue = df["revenue"].sum()

print("\nTotal Revenue:")
print("Rs.", total_revenue)

# Calculate total profit
total_profit = df["profit"].sum()

print("\nTotal Profit:")
print("Rs.", total_profit)


# Calculate total quantity sold for each product
product_sales = df.groupby("product")["quantity"].sum()

print("\nQuantity Sold by Each Product:")
print(product_sales)

# Find the best-selling product
best_product = product_sales.idxmax()

print("\nBest-Selling Product:")
print(best_product)


# Calculate revenue for each city
city_revenue = df.groupby("city")["revenue"].sum()

print("\nRevenue by City:")
print(city_revenue)

# Find the city with the highest revenue
best_city = city_revenue.idxmax()

print("\nCity with Highest Revenue:")
print(best_city)


# Convert order_date into date format
df["order_date"] = pd.to_datetime(df["order_date"])

# Extract month from order date
df["month"] = df["order_date"].dt.month_name()

# Calculate revenue for each month
monthly_revenue = df.groupby("month")["revenue"].sum()

print("\nMonthly Revenue:")
print(monthly_revenue)

# Find the month with highest revenue
best_month = monthly_revenue.idxmax()

print("\nMonth with Highest Revenue:")
print(best_month)
