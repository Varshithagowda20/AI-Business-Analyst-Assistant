# AI Business Analyst Assistant

## Project Overview
The AI Business Analyst Assistant is a Python-based business analytics application that helps users understand sales data through interactive dashboards, visualizations, automated business insights, and an AI-powered question-answering assistant.

Users can explore sales performance, apply filters, download reports, and ask questions in natural language.

## Problem Statement
Businesses collect large amounts of sales data, but understanding that data and identifying useful business insights can be challenging. This project aims to make sales analysis easier through interactive visualizations and AI-generated explanations.

## Technologies Used
- Python – Application development and data analysis
- Pandas – Data processing and analysis
- SQLite – Sales data storage
- Streamlit – Interactive dashboard
- Plotly – Data visualization
- Ollama (Llama 3.2 3B) – Local AI assistant

## Key Features
1. Interactive sales dashboard
2. Revenue and profit analysis
3. City-wise and product-wise performance
4. Category-wise sales analysis
5. Monthly revenue and profit trends
6. City, product, and date filters
7. Product profitability analysis
8. Business KPIs, including Average Order Value
9. Automatic business recommendations
10. CSV report downloads
11. AI-powered business question assistant
12. Conversation history and clear chat option

## How It Works
1. Sales data is generated and stored in a CSV file.
2. The data is loaded into an SQLite database.
3. Python and Pandas process and analyze the data.
4. Streamlit displays interactive dashboards.
5. Plotly creates charts and visualizations.
6. Ollama provides AI-generated explanations using business summary data and conversation history.

## Installation and Execution

Install the required packages:

```bash
python -m pip install pandas streamlit plotly ollama
```

Make sure Ollama is installed and the Llama model is downloaded:

```bash
ollama pull llama3.2:3b
```

Run the application:

```bash
python -m streamlit run app.py
```

## Project Outcome
The application demonstrates how Python, SQL, data visualization, and locally running AI can work together to support business analysis and decision-making.

## Future Enhancements
- Natural-language-to-SQL querying with read-only SQL validation
- Advanced sales forecasting
- Customer segmentation
- More detailed business reports
- Exportable PDF reports