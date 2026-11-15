
import csv
import random
import os
from datetime import datetime, timedelta

# Generate the same sample data whenever we run this program
random.seed(42)

# Sample products and their categories
products = {
    "Laptop": ("Electronics", 50000, 35000),
    "Mobile Phone": ("Electronics", 20000, 14000),
    "Headphones": ("Electronics", 2000, 1000),
    "Office Chair": ("Furniture", 8000, 5000),
    "Desk": ("Furniture", 12000, 8000),
    "Notebook": ("Stationery", 100, 40),
    "Pen": ("Stationery", 20, 8),
    "Backpack": ("Accessories", 1500, 800),
    "Watch": ("Accessories", 3000, 1800)
}

cities = ["Bangalore", "Mumbai", "Delhi", "Chennai", "Hyderabad"]

# Create the data folder if it doesn't exist
os.makedirs("data", exist_ok=True)

# Define the CSV file location
file_path = "data/sales_data.csv"

# Define the starting date
start_date = datetime(2025, 1, 1)

# Create 500 sample orders
with open(file_path, "w", newline="", encoding="utf-8") as file:

    columns = [
        "order_id",
        "order_date",
        "product",
        "category",
        "city",
        "quantity",
        "unit_price",
        "unit_cost",
        "revenue",
        "cost",
        "profit"
    ]

    writer = csv.DictWriter(file, fieldnames=columns)
    writer.writeheader()

    for i in range(1, 501):

        product = random.choice(list(products.keys()))
        category, price, cost_price = products[product]

        quantity = random.randint(1, 5)
        days = random.randint(0, 364)
        order_date = start_date + timedelta(days=days)

        revenue = quantity * price
        total_cost = quantity * cost_price
        profit = revenue - total_cost

        writer.writerow({
            "order_id": i,
            "order_date": order_date.strftime("%Y-%m-%d"),
            "product": product,
            "category": category,
            "city": random.choice(cities),
            "quantity": quantity,
            "unit_price": price,
            "unit_cost": cost_price,
            "revenue": revenue,
            "cost": total_cost,
            "profit": profit
        })

print("Sales dataset created successfully!")
print("Total orders: 500")
print("File location: data/sales_data.csv")
