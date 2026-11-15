
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import ollama

# 1. Page Settings
st.set_page_config(
    page_title="AI Business Analyst Assistant",
    page_icon="📊",
    layout="wide"
)

st.title("📊 AI Business Analyst Assistant")
st.write("Analyze business data and get AI-powered insights.")

# 2. Load Database
connection = sqlite3.connect("data/business.db")
df = pd.read_sql_query("SELECT * FROM sales", connection)
connection.close()

df["order_date"] = pd.to_datetime(df["order_date"])

# 3. Sidebar Filters
st.sidebar.header("Sales Filters")

selected_city = st.sidebar.selectbox(
    "Select City",
    ["All Cities"] + sorted(df["city"].unique().tolist())
)

selected_product = st.sidebar.selectbox(
    "Select Product",
    ["All Products"] + sorted(df["product"].unique().tolist())
)

filtered_df = df.copy()

# Date Range Filter

st.sidebar.subheader("Select Date Range")

start_date = st.sidebar.date_input(
    "Start Date",
    df["order_date"].min().date()
)

end_date = st.sidebar.date_input(
    "End Date",
    df["order_date"].max().date()
)

filtered_df = filtered_df[
    (filtered_df["order_date"].dt.date >= start_date) &
    (filtered_df["order_date"].dt.date <= end_date)
]


if selected_city != "All Cities":
    filtered_df = filtered_df[
        filtered_df["city"] == selected_city
    ]

if selected_product != "All Products":
    filtered_df = filtered_df[
        filtered_df["product"] == selected_product
    ]

# 4. Business Metrics
st.subheader("📈 Business Performance")

total_revenue = filtered_df["revenue"].sum()
total_profit = filtered_df["profit"].sum()
total_orders = filtered_df["order_id"].nunique()

col1, col2, col3 = st.columns(3)

col1.metric("Total Revenue", f"₹{total_revenue:,.2f}")
col2.metric("Total Profit", f"₹{total_profit:,.2f}")
col3.metric("Total Orders", total_orders)


# Additional Business KPIs

st.subheader("Additional Business KPIs")

total_orders = filtered_df["order_id"].nunique()

total_units = filtered_df["quantity"].sum()

average_order_value = (
    filtered_df["revenue"].sum() / total_orders
    if total_orders > 0 else 0
)

average_profit_per_order = (
    filtered_df["profit"].sum() / total_orders
    if total_orders > 0 else 0
)

col1, col2, col3 = st.columns(3)

col1.metric("Total Units Sold", f"{total_units:,}")

col2.metric("Average Order Value", f"₹{average_order_value:,.2f}")

col3.metric("Average Profit per Order", f"₹{average_profit_per_order:,.2f}")

# 5. Revenue by City
st.subheader("🌆 Revenue by City")

city_revenue = (
    filtered_df.groupby("city")["revenue"]
    .sum()
    .reset_index()
)

fig_city = px.bar(
    city_revenue,
    x="city",
    y="revenue",
    title="Revenue by City"
)

st.plotly_chart(fig_city, use_container_width=True)

# Profit Comparison by City

st.subheader("Profit Comparison by City")

city_profit = (
    filtered_df.groupby("city")["profit"]
    .sum()
    .reset_index()
    .sort_values(by="profit", ascending=False)
)

fig_city_profit = px.bar(
    city_profit,
    x="city",
    y="profit",
    title="Total Profit by City",
    text_auto=True
)

st.plotly_chart(fig_city_profit, use_container_width=True)

# 6. Monthly Revenue
st.subheader("📅 Monthly Revenue Analysis")

monthly_revenue = (
    filtered_df.assign(
        month=filtered_df["order_date"].dt.to_period("M").astype(str)
    )
    .groupby("month")["revenue"]
    .sum()
    .reset_index()
)

fig_month = px.line(
    monthly_revenue,
    x="month",
    y="revenue",
    title="Monthly Revenue Trend",
    markers=True
)

st.plotly_chart(fig_month, use_container_width=True)

# Monthly Profit Trend

st.subheader("Monthly Profit Trend")

monthly_profit = (
    filtered_df.groupby(
        filtered_df["order_date"].dt.to_period("M")
    )["profit"]
    .sum()
    .reset_index()
)

monthly_profit["order_date"] = (
    monthly_profit["order_date"].astype(str)
)

fig_monthly_profit = px.line(
    monthly_profit,
    x="order_date",
    y="profit",
    title="Monthly Profit Trend",
    markers=True
)

st.plotly_chart(
    fig_monthly_profit,
    use_container_width=True
)

# 7. Product Performance
st.subheader("📦 Product Performance")

product_data = (
    filtered_df.groupby("product")
    .agg(
        revenue=("revenue", "sum"),
        profit=("profit", "sum"),
        quantity=("quantity", "sum")
    )
    .reset_index()
)

fig_product = px.bar(
    product_data.sort_values("revenue", ascending=False),
    x="product",
    y="revenue",
    title="Revenue by Product"
)

st.plotly_chart(fig_product, use_container_width=True)

# Sales Performance by Category

st.subheader("Sales Performance by Category")

category_sales = (
    filtered_df.groupby("category")["revenue"]
    .sum()
    .reset_index()
)

fig_category = px.bar(
    category_sales,
    x="category",
    y="revenue",
    title="Revenue by Product Category",
    text_auto=True
)

st.plotly_chart(fig_category, use_container_width=True)

# Profit Analysis by Category

st.subheader("Profit Analysis by Category")

category_profit = (
    filtered_df.groupby("category")["profit"]
    .sum()
    .reset_index()
    .sort_values(by="profit", ascending=False)
)

fig_profit = px.bar(
    category_profit,
    x="category",
    y="profit",
    title="Profit by Product Category",
    text_auto=True
)

st.plotly_chart(fig_profit, use_container_width=True)

# Product Profitability Analysis

st.subheader("Products Needing Attention")

product_analysis = (
    filtered_df.groupby("product")
    .agg(
        Revenue=("revenue", "sum"),
        Profit=("profit", "sum")
    )
    .reset_index()
)

product_analysis["Profit Margin (%)"] = (
    product_analysis["Profit"] /
    product_analysis["Revenue"] * 100
)

product_analysis = product_analysis.sort_values(
    by="Profit Margin (%)",
    ascending=True
)

st.dataframe(product_analysis, use_container_width=True)

st.caption(
    "Products at the top have the lowest profit margins "
    "and may need pricing or cost review."
)


# 8. Advanced Business Insights
st.subheader("💡 Advanced Business Insights")

if not filtered_df.empty:

    best_city = city_revenue.loc[
        city_revenue["revenue"].idxmax(), "city"
    ]

    best_revenue_product = product_data.loc[
        product_data["revenue"].idxmax(), "product"
    ]

    best_profit_product = product_data.loc[
        product_data["profit"].idxmax(), "product"
    ]

    profit_margin = (
        (total_profit / total_revenue) * 100
        if total_revenue != 0 else 0
    )

    col1, col2, col3 = st.columns(3)

    col1.metric("Highest Revenue City", best_city)
    col2.metric("Top Revenue Product", best_revenue_product)
    col3.metric("Top Profit Product", best_profit_product)

    st.metric("Profit Margin", f"{profit_margin:.2f}%")

else:
    st.warning("No data available for selected filters.")

# Automatic Business Recommendations

st.subheader("Business Recommendations")

if not filtered_df.empty:

    best_city = (
        filtered_df.groupby("city")["profit"]
        .sum()
        .idxmax()
    )

    best_category = (
        filtered_df.groupby("category")["revenue"]
        .sum()
        .idxmax()
    )

    product_profit = (
        filtered_df.groupby("product")["profit"]
        .sum()
    )

    lowest_profit_product = product_profit.idxmin()

    st.write("1. **Best Performing City:**")
    st.write(
        f"{best_city} generates the highest total profit."
    )

    st.write("2. **Best Revenue Category:**")
    st.write(
        f"{best_category} generates the highest revenue."
    )

    st.write("3. **Product Requiring Attention:**")
    st.write(
        f"{lowest_profit_product} has the lowest total profit."
    )

else:
    st.warning("No sales data available for the selected filters.")

# 9. AI Business Question Assistant
st.subheader("🤖 AI Business Question Assistant")

question = st.text_input(
    "Ask your business question:",
    placeholder="Example: Explain my business performance"
)

if st.button("Ask AI"):

    if not question.strip():
        st.warning("Please enter a question.")

    elif filtered_df.empty:
        st.warning("No business data available.")

    else:

        business_data = f"""
        Total Revenue: ₹{total_revenue:,.2f}
        Total Profit: ₹{total_profit:,.2f}
        Total Orders: {total_orders}
        Total Quantity Sold: {filtered_df['quantity'].sum()}

        Highest Revenue City: {best_city}
        Highest Revenue Product: {best_revenue_product}
        Most Profitable Product: {best_profit_product}
        Profit Margin: {profit_margin:.2f}%

        Revenue by City:
        {city_revenue.to_string(index=False)}

        Product Performance:
        {product_data.to_string(index=False)}
        """

        prompt = f"""
        You are a professional Business Analyst Assistant.

        Use only the business data provided below.
        Answer in simple English.
        Explain useful business insights.
        Never invent numbers.

        Business Data:
        {business_data}

        User Question:
        {question}
        """

        try:
            with st.spinner("AI is analyzing your business data..."):

                response = ollama.chat(
                    model="llama3.2:3b",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

            st.success("AI Analysis Completed!")

            st.write(response["message"]["content"])

        except Exception as e:
            st.error(f"AI connection error: {e}")

# AI Business Chat Assistant with Conversation Memory

st.subheader("AI Business Chat Assistant")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if st.button("Clear Chat History"):
    st.session_state.chat_history = []
    st.rerun()

# Display previous messages
for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Get a new question
user_question = st.chat_input("Ask a business question...")

if user_question:

    st.session_state.chat_history.append({
        "role": "user",
        "content": user_question
    })

    with st.chat_message("user"):
        st.markdown(user_question)

    business_summary = f"""
    Total Revenue: {filtered_df['revenue'].sum():.2f}
    Total Profit: {filtered_df['profit'].sum():.2f}
    Total Orders: {filtered_df['order_id'].nunique()}
    Total Units Sold: {filtered_df['quantity'].sum()}
    """

    messages = [
        {
            "role": "system",
            "content": (
                "You are a professional Business Analyst. "
                "Analyze the provided business data. "
                "Give simple explanations and practical recommendations. "
                "Do not invent numbers."
                f"\nBusiness Data:\n{business_summary}"
            )
        }
    ] + st.session_state.chat_history

    with st.chat_message("assistant"):
        with st.spinner("AI is analyzing..."):
            response = ollama.chat(
                model="llama3.2:3b",
                messages=messages
            )

            ai_answer = response["message"]["content"]
            st.markdown(ai_answer)

    st.session_state.chat_history.append({
        "role": "assistant",
        "content": ai_answer
    })


# Download Business Report

st.subheader("Download Business Report")

csv_data = filtered_df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Filtered Sales Data",
    data=csv_data,
    file_name="business_sales_report.csv",
    mime="text/csv"
)