import sqlite3

connection = sqlite3.connect("data/business.db")
cursor = connection.cursor()

# Question 1: Total Revenue
cursor.execute("SELECT SUM(revenue) FROM sales")
print("Total Revenue:", cursor.fetchone()[0])

# Question 2: Total Profit
cursor.execute("SELECT SUM(profit) FROM sales")
print("Total Profit:", cursor.fetchone()[0])

# Question 3: City with Highest Revenue
cursor.execute("""
    SELECT city, SUM(revenue) AS total_revenue
    FROM sales
    GROUP BY city
    ORDER BY total_revenue DESC
    LIMIT 1
""")
print("Highest Revenue City:", cursor.fetchone())

# Question 4: Best Selling Product by Quantity
cursor.execute("""
    SELECT product, SUM(quantity) AS total_quantity
    FROM sales
    GROUP BY product
    ORDER BY total_quantity DESC
    LIMIT 1
""")
print("Best Selling Product:", cursor.fetchone())

# Question 5: Total Orders
cursor.execute("SELECT COUNT(*) FROM sales")
print("Total Orders:", cursor.fetchone()[0])

connection.close()