"""
AI Business Analyst Assistant  -  Universal CSV Edition (v3)

Upload ANY CSV. The app detects column meaning, builds filters, KPIs, charts,
insights, recommendations, a custom chart builder, and a chat assistant that
answers most questions instantly with pandas (no AI needed) and uses a local
Ollama model for everything else.

Run:   streamlit run app.py
Needs: pip install streamlit pandas numpy plotly ollama openpyxl
AI:    ollama pull llama3.2:1b   (Ollama must be running; optional)
"""

import html
import io
import itertools
import os
import re
import sqlite3
import warnings

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False


# =========================================================
# 1. PAGE CONFIG + THEME
# =========================================================

st.set_page_config(
    page_title="AI Business Analyst Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp { background-color:#F4F7FC !important; color:#243247 !important; }
.block-container { max-width:1450px; padding-top:1.5rem; padding-bottom:2rem; }
h1 { color:#173B65 !important; font-weight:800 !important; letter-spacing:-0.8px; }
h2, h3 { color:#193D63 !important; font-weight:700 !important; }
p { color:#40536B; }
.subtitle { color:#64748B !important; font-size:15px; margin-top:-8px; margin-bottom:18px; }

section[data-testid="stSidebar"] { background-color:#EAF0F8 !important; border-right:1px solid #D9E3F0; }
section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color:#193D63 !important; }
section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] label { color:#29435F !important; }

button[data-baseweb="tab"] { font-weight:700 !important; }

div[data-testid="stMetric"] {
    background-color:#FFFFFF !important; border:1px solid #DFE7F1 !important;
    border-radius:14px !important; padding:20px !important; min-height:112px;
    box-shadow:0 4px 14px rgba(30,55,90,0.06); transition:0.2s ease;
}
div[data-testid="stMetric"]:hover { border-color:#AFC6E0 !important; box-shadow:0 6px 18px rgba(30,55,90,0.10); }
div[data-testid="stMetricLabel"] { color:#64748B !important; font-size:13px !important; font-weight:600 !important; }
div[data-testid="stMetricValue"] { color:#173B65 !important; font-size:24px !important; font-weight:800 !important; }

.stButton > button, .stDownloadButton > button {
    background-color:#245A91 !important; color:#FFFFFF !important; border:1px solid #245A91 !important;
    border-radius:9px !important; font-weight:700 !important; padding:10px 18px !important;
}
.stButton > button p, .stDownloadButton > button p { color:#FFFFFF !important; }
.stButton > button:hover, .stDownloadButton > button:hover { background-color:#173B65 !important; border-color:#173B65 !important; }

div[data-testid="stFileUploader"] { background-color:#FFFFFF !important; border:1px dashed #A8BED8 !important; border-radius:11px !important; padding:10px !important; }
div[data-testid="stPlotlyChart"] { background-color:#FFFFFF !important; border:1px solid #E1E8F0 !important; border-radius:13px !important; padding:9px !important; }
div[data-testid="stDataFrame"] { background-color:#FFFFFF !important; border:1px solid #DFE7F1 !important; border-radius:11px !important; overflow:hidden; }
div[data-testid="stAlert"] { border-radius:9px !important; }
hr { border-color:#DFE7F1 !important; }

.hero { background:linear-gradient(135deg,#173B65 0%,#245A91 55%,#3B82C4 100%); border-radius:18px;
        padding:24px 30px 18px 30px; margin-bottom:18px; box-shadow:0 8px 24px rgba(23,59,101,0.22); }
.hero-title { font-size:23px; font-weight:800; color:#FFFFFF; }
.hero-sub { font-size:14px; color:#DCEAFE; margin-top:4px; }
.chip { display:inline-block; background:rgba(255,255,255,0.16); border:1px solid rgba(255,255,255,0.30);
        color:#FFFFFF; padding:5px 13px; border-radius:999px; font-size:12.5px; font-weight:600; margin:12px 8px 0 0; }

.rec-card { background-color:#FFFFFF; border:1px solid #DFE7F1; border-radius:12px; padding:17px;
            min-height:145px; box-shadow:0 3px 10px rgba(30,55,90,0.04); }

.footer { text-align:center; color:#64748B !important; font-size:12px; line-height:1.9; padding:15px 0 5px 0; }
.footer strong { color:#173B65 !important; font-size:14px; }
</style>
""", unsafe_allow_html=True)


# =========================================================
# 2. SMALL HELPERS
# =========================================================

CHART_LAYOUT = {
    "template": "plotly_white",
    "font": {"family": "Arial", "color": "#263A53", "size": 12},
    "paper_bgcolor": "#FFFFFF",
    "plot_bgcolor": "#FFFFFF",
    "margin": dict(l=20, r=20, t=65, b=25),
    "title_font": {"size": 17, "color": "#193D63"},
}
BLUE_SCALE = ["#B9D7F2", "#245A91"]
GREEN_SCALE = ["#B8E3D1", "#23866B"]
PALETTE = px.colors.qualitative.Safe

_chart_counter = itertools.count()          # unique key for every chart in a run
_ST_VERSION = tuple(int(p) for p in re.findall(r"\d+", st.__version__)[:2])


def show_chart(fig):
    """Display a Plotly figure (works on old and new Streamlit versions)."""
    fig.update_layout(**CHART_LAYOUT)
    key = f"chart_{next(_chart_counter)}"
    if _ST_VERSION >= (1, 50):
        try:
            st.plotly_chart(fig, width="stretch", key=key)
            return
        except TypeError:
            pass
    st.plotly_chart(fig, use_container_width=True, key=key)


def show_table(data, **kwargs):
    if _ST_VERSION >= (1, 50):
        try:
            st.dataframe(data, width="stretch", hide_index=True, **kwargs)
            return
        except TypeError:
            pass
    st.dataframe(data, use_container_width=True, hide_index=True, **kwargs)


def norm(name) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).lower()).strip("_")


def name_has(name, words) -> bool:
    """True if a column name contains any word (as a whole token, or as a substring for long words)."""
    n = norm(name)
    tokens = set(n.split("_"))
    for w in words:
        if w in tokens or w + "s" in tokens or w + "es" in tokens:
            return True
        if len(w) >= 6 and w in n:
            return True
    return False


def pick(columns, include, exclude=()):
    """First column (by keyword priority) containing an include word and no exclude word."""
    for key in include:
        for col in columns:
            n = norm(col)
            if key in n and not any(e in n for e in exclude):
                return col
    return None


def find_col(columns, keywords):
    return pick(columns, keywords)


def aggregate(df, by, metric, agg):
    """Group by column(s) and aggregate. metric=None or agg='count' -> row count."""
    by = by if isinstance(by, list) else [by]
    if metric is None or agg == "count" or metric in by:
        out = df.groupby(by).size().reset_index(name="count")
        return out, "count"
    out = df.groupby(by)[metric].agg(agg).reset_index()
    return out, metric


def fmt(value, col=None):
    if value is None or pd.isna(value):
        return "-"
    return f"{value:,.2f}"


# =========================================================
# 3. DATA LOADING + AUTOMATIC CLEANING
# =========================================================

DATE_HINTS = ("date", "time", "day", "month", "year", "created", "updated", "dob",
              "timestamp", "signup", "joined", "registered", "hire", "birth")
PCT_WORDS = ("percent", "percentage", "margin", "pct", "ratio", "discount")
SUM_WORDS = ("revenue", "sales", "amount", "cost", "profit", "expense", "spend", "budget",
             "turnover", "payment", "quantity", "qty", "units", "orders", "stock", "count",
             "visits", "clicks", "views", "sessions", "items")


def default_agg(col) -> str:
    """Sensible default aggregation: totals for money/volume, averages for everything else."""
    return "sum" if col and name_has(col, SUM_WORDS) else "mean"


@st.cache_data(show_spinner=False)
def read_csv_bytes(raw: bytes) -> pd.DataFrame:
    """Read a CSV with automatic delimiter + encoding detection."""
    last_error = None
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(raw), sep=None, engine="python",
                               encoding=encoding, on_bad_lines="skip")
        except Exception as exc:
            last_error = exc
    raise ValueError(f"Could not read this CSV: {last_error}")


def make_sample_data() -> pd.DataFrame:
    """Built-in demo sales data (used only if no upload and no default database)."""
    rng = np.random.default_rng(42)
    n = 800
    catalog = {
        "Laptop": ("Electronics", 55000), "Smartphone": ("Electronics", 28000),
        "Headphones": ("Accessories", 3500), "Keyboard": ("Accessories", 1800),
        "Office Chair": ("Furniture", 9500), "Desk": ("Furniture", 14000),
        "Notebook": ("Stationery", 120), "Pen Set": ("Stationery", 350),
    }
    products = rng.choice(list(catalog), n)
    qty = rng.integers(1, 6, n)
    price = np.array([catalog[p][1] for p in products])
    revenue = price * qty
    cost = revenue * rng.uniform(0.60, 0.92, n)
    dates = pd.to_datetime("2025-01-01") + pd.to_timedelta(rng.integers(0, 365, n), unit="D")
    return pd.DataFrame({
        "order_id": [f"ORD{1000 + i}" for i in range(n)],
        "order_date": dates.strftime("%Y-%m-%d"),
        "product": products,
        "category": [catalog[p][0] for p in products],
        "city": rng.choice(["Bengaluru", "Mumbai", "Delhi", "Chennai", "Hyderabad", "Pune"], n),
        "quantity": qty,
        "revenue": revenue,
        "cost": cost.round(2),
        "profit": (revenue - cost).round(2),
    })


def load_default():
    """Default data: data/business.db -> sales table (falls back to built-in sample)."""
    path = "data/business.db"
    if os.path.exists(path):
        try:
            conn = sqlite3.connect(path)
            try:
                return pd.read_sql("SELECT * FROM sales", conn), "default database"
            finally:
                conn.close()
        except Exception:
            pass
    return make_sample_data(), "built-in sample data"


def guess_dayfirst(frame: pd.DataFrame) -> bool:
    """True when text dates clearly look like DD-MM-YYYY (a first number above 12)."""
    pattern = re.compile(r"^\s*(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})")
    first_big = second_big = False
    for col in frame.columns:
        if pd.api.types.is_numeric_dtype(frame[col]) or pd.api.types.is_datetime64_any_dtype(frame[col]):
            continue
        for value in frame[col].dropna().astype(str).head(300):
            m = pattern.match(value)
            if m:
                first_big |= int(m.group(1)) > 12
                second_big |= int(m.group(2)) > 12
    return first_big and not second_big


@st.cache_data(show_spinner=False)
def smart_convert(df: pd.DataFrame, dayfirst: bool):
    """Detect numbers/dates stored as text and convert them. Returns (df, notes)."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").dropna(axis=1, how="all")
    notes = []

    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]) or pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        original = df[col]
        text = original.astype("string").str.strip()
        non_null = int(text.notna().sum())
        if non_null == 0:
            continue

        # numbers hidden in text:  "₹1,200"  "45%"  "3 500"
        cleaned = text.str.replace(r"[₹$€£,%\s]", "", regex=True)
        numeric = pd.to_numeric(cleaned, errors="coerce")
        if numeric.notna().sum() / non_null >= 0.90:
            df[col] = numeric
            notes.append(f"'{col}' converted from text to numbers")
            continue

        # dates hidden in text
        hinted = any(h in col.lower() for h in DATE_HINTS)
        looks_like_date = text.dropna().head(200).str.contains(r"[-/:]", regex=True).mean() > 0.8
        if hinted or looks_like_date:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                sample = pd.to_datetime(text.dropna().head(300), errors="coerce", dayfirst=dayfirst)
            if sample.notna().mean() >= 0.80:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    df[col] = pd.to_datetime(text, errors="coerce", dayfirst=dayfirst)
                notes.append(f"'{col}' converted from text to dates")
                continue

        df[col] = original.astype("object")
    return df, notes


def classify_columns(df: pd.DataFrame) -> dict:
    """Classify columns conservatively so identifiers are never treated as measures."""
    n = max(len(df), 1)
    types = {"numeric": [], "categorical": [], "datetime": [], "id": [], "text": []}
    category_words = ("status", "type", "category", "segment", "gender", "city", "country",
                      "region", "department", "product", "brand", "membership", "channel",
                      "class", "level", "grade", "tier")
    cat_limit = min(60, max(12, int(np.sqrt(n) * 2)))

    for col in df.columns:
        s = df[col]
        name = norm(col)
        tokens = set(name.split("_"))
        nun = int(s.nunique(dropna=True))
        ratio = nun / n
        id_hint = bool(tokens & {"id", "uuid", "guid", "index", "sku"}) or any(
            w in name for w in ("customerid", "employeeid", "orderid", "productid", "transactionid"))

        if pd.api.types.is_datetime64_any_dtype(s):
            types["datetime"].append(col)
        elif pd.api.types.is_bool_dtype(s):
            types["categorical"].append(col)
        elif pd.api.types.is_numeric_dtype(s):
            vals = s.dropna()
            integer_like = len(vals) > 0 and bool(np.isclose(vals % 1, 0).all())
            sequential_id = (integer_like and ratio >= 0.90 and n >= 8
                             and (vals.is_monotonic_increasing or vals.is_monotonic_decreasing))
            if (id_hint and ratio >= 0.20) or sequential_id:
                types["id"].append(col)
            else:
                types["numeric"].append(col)
                if integer_like and nun <= 12 and tokens & set(category_words):
                    types["categorical"].append(col)
        else:
            if id_hint and ratio >= 0.20:
                types["id"].append(col)
            elif nun <= cat_limit:
                types["categorical"].append(col)
            else:
                types["text"].append(col)
    return types


def detect_semantic_roles(df: pd.DataFrame, types: dict) -> dict:
    """Infer likely business meaning of each numeric column from its name."""
    roles = {"money": [], "quantity": [], "rating": [], "age": [], "percentage": [],
             "date": list(types["datetime"]), "identifier": list(types["id"])}
    money_w = ("revenue", "sales", "amount", "price", "cost", "profit", "income", "expense",
               "salary", "budget", "spend", "value", "turnover", "payment", "balance",
               "fee", "charge", "wage", "pay")
    qty_w = ("quantity", "qty", "units", "unit", "orders", "count", "stock", "inventory",
             "employees", "customers", "items", "visits", "clicks", "views", "sessions")
    rating_w = ("rating", "score", "satisfaction", "review", "rank", "grade", "stars", "marks")

    for col in types["numeric"]:
        if name_has(col, PCT_WORDS):
            roles["percentage"].append(col)
        elif name_has(col, money_w):
            roles["money"].append(col)
        elif name_has(col, qty_w):
            roles["quantity"].append(col)
        elif name_has(col, rating_w):
            roles["rating"].append(col)
        elif name_has(col, ("age",)):
            roles["age"].append(col)
        elif name_has(col, ("rate",)):
            roles["percentage"].append(col)

    used = set().union(*[set(roles[k]) for k in ("money", "quantity", "rating", "age", "percentage")])
    roles["other_measures"] = [c for c in types["numeric"] if c not in used]
    roles["dimensions"] = list(types["categorical"])
    return roles


def detect_dataset_domain(df: pd.DataFrame) -> str:
    """Best-effort dataset label used only for friendlier wording."""
    names = " ".join(norm(c).replace("_", " ") for c in df.columns)
    patterns = [
        ("Sales / Retail", ("revenue", "sales", "order", "product", "quantity", "profit")),
        ("Customer Analysis", ("customer", "membership", "signup", "satisfaction", "churn")),
        ("Employee / HR", ("employee", "department", "salary", "hire", "performance", "attendance")),
        ("Finance", ("transaction", "balance", "account", "payment", "expense", "budget")),
        ("Inventory", ("stock", "warehouse", "sku", "inventory", "supplier", "reorder")),
        ("Student / Education", ("student", "grade", "marks", "course", "attendance", "semester")),
        ("Marketing", ("campaign", "click", "impression", "conversion", "lead", "channel")),
    ]
    scores = [(label, sum(1 for w in words if w in names)) for label, words in patterns]
    label, score = max(scores, key=lambda x: x[1])
    return label if score >= 2 else "General Dataset"


# =========================================================
# 4. SIDEBAR - DATA SOURCE
# =========================================================

st.title("📊 AI Business Analyst Assistant")
st.markdown('<p class="subtitle">Upload any CSV - columns, filters, KPIs, charts, insights and AI '
            'analysis adapt automatically.</p>', unsafe_allow_html=True)

st.sidebar.markdown("## 📁 Data Source")
uploaded_file = st.sidebar.file_uploader("Upload any CSV file", type=["csv"])

try:
    if uploaded_file is not None:
        raw_df = read_csv_bytes(uploaded_file.getvalue())
        source_label = uploaded_file.name
        st.sidebar.success(f"Loaded {uploaded_file.name}")
    else:
        raw_df, source_label = load_default()
        st.sidebar.info(f"Using {source_label}")
except Exception as exc:
    st.error(f"Unable to load data: {exc}")
    st.stop()

# Stable id for this dataset: widget keys include it so filters reset cleanly on a new file.
dsk = abs(hash((source_label, tuple(map(str, raw_df.columns))))) % 10**8

dayfirst = st.sidebar.checkbox("Dates are DD-MM-YYYY (day first)",
                               value=guess_dayfirst(raw_df), key=f"dayfirst_{dsk}")

df, conversion_notes = smart_convert(raw_df, dayfirst)
if df.empty:
    st.error("The file has no usable rows.")
    st.stop()

types = classify_columns(df)
roles = detect_semantic_roles(df, types)
dataset_domain = detect_dataset_domain(df)
all_cols = list(df.columns)
numeric_cols = types["numeric"]

# Business columns (used only when present - the app works without them)
_not_pct = ("percent", "pct", "ratio", "rate", "margin")
revenue_col = pick(numeric_cols, ["revenue", "sales", "turnover", "amount", "total"],
                   exclude=("cost", "expense", "tax", "discount", "profit", "avg", "average", "growth") + _not_pct)
profit_col = pick(numeric_cols, ["profit", "earnings", "net_income"], exclude=_not_pct)
cost_col = pick(numeric_cols, ["cost", "expense"], exclude=_not_pct)
qty_col = pick(numeric_cols, ["quantity", "qty", "units"], exclude=_not_pct)
order_col = pick(types["id"], ["order", "invoice", "transaction", "txn"])
is_sales = bool(revenue_col) and (dataset_domain == "Sales / Retail"
                                  or name_has(revenue_col, ("revenue", "sales", "turnover")))


# =========================================================
# 5. SIDEBAR - ANALYSIS SETTINGS + FILTERS
# =========================================================

st.sidebar.markdown("---")
st.sidebar.markdown("## ⚙️ Analysis Settings")

AGG_OPTIONS = ["sum", "mean", "median", "min", "max", "count"]
if numeric_cols:
    preferred = [c for c in [revenue_col, profit_col] if c] + roles["money"] + roles["quantity"] \
        + roles["rating"] + roles["age"] + roles["other_measures"] + numeric_cols
    default_metric = preferred[0]
    metric = st.sidebar.selectbox("Primary metric", numeric_cols,
                                  index=numeric_cols.index(default_metric), key=f"metric_{dsk}")
    agg = st.sidebar.selectbox("Aggregation", AGG_OPTIONS,
                               index=AGG_OPTIONS.index(default_agg(metric)))
else:
    metric, agg = None, "count"
    st.sidebar.caption("No numeric measures found - charts will count records.")

st.sidebar.markdown("---")
st.sidebar.markdown("## 🎯 Dashboard Filters")


def reset_filters():
    for k in [k for k in st.session_state if str(k).startswith("flt_")]:
        del st.session_state[k]


st.sidebar.button("🔄 Reset all filters", on_click=reset_filters)

fdf = df.copy()
date_col = None

if types["datetime"]:
    date_col = st.sidebar.selectbox("Date column", types["datetime"], key=f"flt_datecol_{dsk}")
    valid_dates = df[date_col].dropna()
    d_min, d_max = valid_dates.min().date(), valid_dates.max().date()
    picked = st.sidebar.date_input("Date range", value=(d_min, d_max), min_value=d_min,
                                   max_value=d_max, key=f"flt_dates_{dsk}")
    if isinstance(picked, (tuple, list)) and len(picked) == 2:
        fdf = fdf[(fdf[date_col].dt.date >= picked[0]) & (fdf[date_col].dt.date <= picked[1])]

cat_filter_cols = st.sidebar.multiselect("Filter by categories", types["categorical"],
                                         default=types["categorical"][:2], key=f"flt_cats_{dsk}")
for col in cat_filter_cols:
    options = sorted(df[col].dropna().astype(str).unique().tolist())
    chosen = st.sidebar.multiselect(f"{col} (empty = all)", options, key=f"flt_cat_{col}_{dsk}")
    if chosen:
        fdf = fdf[fdf[col].astype(str).isin(chosen)]

num_filter_cols = st.sidebar.multiselect("Filter by number ranges", numeric_cols, key=f"flt_nums_{dsk}")
for col in num_filter_cols:
    lo, hi = float(df[col].min()), float(df[col].max())
    if lo < hi:
        low, high = st.sidebar.slider(col, lo, hi, (lo, hi), key=f"flt_num_{col}_{dsk}")
        fdf = fdf[fdf[col].between(low, high)]

st.sidebar.markdown("---")
st.sidebar.caption("Python • Pandas • Plotly • Streamlit • Ollama")

if fdf.empty:
    st.warning("No records match the selected filters. Please change your filters.")
    st.stop()


# =========================================================
# 6. ANALYTICS ENGINE (insights, health, outliers, answers)
# =========================================================

def monthly_series(data, col, how):
    """Monthly aggregated series for a metric (None if not possible)."""
    if not date_col or col is None:
        return None
    grouped = data.groupby(pd.Grouper(key=date_col, freq="MS"))[col]
    series = grouped.agg("count" if how == "count" else how).dropna()
    return series if len(series) >= 2 else None


def outlier_table(data):
    rows = []
    for c in numeric_cols:
        s = data[c].dropna()
        if len(s) < 8:
            continue
        q1, q3 = s.quantile([0.25, 0.75])
        iqr = q3 - q1
        if iqr == 0:
            continue
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        n_out = int(((s < lo) | (s > hi)).sum())
        rows.append({"Column": c, "Outliers": n_out, "Outlier %": round(n_out / len(s) * 100, 2),
                     "Lower Bound": round(lo, 2), "Upper Bound": round(hi, 2)})
    return pd.DataFrame(rows)


def health_score(data) -> int:
    missing = data.isna().mean().mean() * 100
    dup = data.duplicated().mean() * 100
    score = 100 - min(45, missing * 2.5) - min(25, dup * 2.5)
    ot = outlier_table(data)
    if not ot.empty:
        score -= min(15, ot["Outlier %"].mean() * 1.5)
    return int(max(0, round(score)))


def auto_insights(data) -> list:
    out = []
    label = metric or "records"

    for col in roles["dimensions"][:3]:
        grouped, val = aggregate(data, col, metric, agg)
        if len(grouped) < 2:
            continue
        grouped = grouped.sort_values(val, ascending=False)
        top, bottom = grouped.iloc[0], grouped.iloc[-1]
        msg = f"**{col}:** '{top[col]}' leads ({agg} of {label}: {fmt(top[val])})"
        total = grouped[val].sum()
        if agg in ("sum", "count") and total > 0:
            msg += f", about {top[val] / total * 100:.1f}% of the total"
        out.append(msg + f". Lowest is '{bottom[col]}' ({fmt(bottom[val])}).")

    trend = monthly_series(data, metric, agg)
    if trend is not None:
        last, prev = trend.iloc[-1], trend.iloc[-2]
        if prev != 0:
            out.append(f"**Trend:** latest month ({trend.index[-1]:%b %Y}) is {fmt(last)}, "
                       f"{(last - prev) / abs(prev) * 100:+.1f}% vs the previous month.")
        out.append(f"**Peak month:** {trend.idxmax():%b %Y} ({fmt(trend.max())}).")

    if agg in ("sum", "count") and metric and roles["dimensions"]:
        grouped, val = aggregate(data, roles["dimensions"][0], metric, agg)
        grouped = grouped.sort_values(val, ascending=False)
        total = grouped[val].sum()
        if len(grouped) >= 5 and total > 0:
            n80 = int(((grouped[val].cumsum() / total * 100) < 80).sum() + 1)
            out.append(f"**Pareto:** {n80} of {len(grouped)} {roles['dimensions'][0]} values "
                       f"({n80 / len(grouped) * 100:.0f}%) generate 80% of {label}.")

    nums = numeric_cols[:30]
    if len(nums) >= 2:
        corr = data[nums].corr().abs()
        corr = corr.where(~np.eye(len(corr), dtype=bool)).stack()
        if not corr.empty:
            a, b = corr.idxmax()
            r = data[[a, b]].corr().iloc[0, 1]
            if abs(r) >= 0.5:
                how = "rise together" if r > 0 else "move in opposite directions"
                out.append(f"**Relationship:** '{a}' and '{b}' {how} (correlation {r:.2f}).")

    miss = data.isna().mean() * 100
    bad = miss[miss > 20]
    if not bad.empty:
        out.append("**Data quality:** more than 20% missing in " + ", ".join(f"'{c}'" for c in bad.index) + ".")
    return out


def recommendations(data) -> list:
    out = []
    label = metric or "records"
    for col in roles["dimensions"][:2]:
        grouped, val = aggregate(data, col, metric, agg)
        if len(grouped) < 2:
            continue
        grouped = grouped.sort_values(val, ascending=False)
        out.append(f"Double down on **{grouped.iloc[0][col]}** ({col}): it leads on {agg} of {label}.")
        out.append(f"Investigate **{grouped.iloc[-1][col]}** ({col}): lowest {agg} of {label}. "
                   f"Check pricing, cost or demand.")

    if revenue_col and profit_col and roles["dimensions"]:
        dim = find_col(roles["dimensions"], ["product", "item", "category", "service"]) or roles["dimensions"][0]
        g = data.groupby(dim).agg(rev=(revenue_col, "sum"), prof=(profit_col, "sum"))
        g = g[g["rev"] > 0]
        if len(g) >= 2:
            g["margin"] = g["prof"] / g["rev"] * 100
            low = g["margin"].idxmin()
            overall = data[profit_col].sum() / max(data[revenue_col].sum(), 1e-9) * 100
            out.append(f"Review pricing and costs for **{low}** ({dim}): margin is "
                       f"{g.loc[low, 'margin']:.1f}% vs {overall:.1f}% overall.")

    trend = monthly_series(data, metric, agg)
    if trend is not None and len(trend) >= 4 and (trend.tail(4).diff().dropna() < 0).all():
        out.append(f"**{metric}** has fallen three months in a row. Find out what changed.")

    miss = data.isna().mean() * 100
    for col in miss[miss > 5].sort_values(ascending=False).index[:2]:
        out.append(f"Fix missing values in **{col}** ({miss[col]:.1f}% empty) before relying on it.")

    ot = outlier_table(data)
    if not ot.empty:
        for _, row in ot[ot["Outlier %"] > 5].head(1).iterrows():
            out.append(f"Check **{row['Column']}**: {row['Outlier %']:.1f}% of values are statistical outliers.")
    return out[:8]


def executive_summary(data) -> str:
    article = "an" if dataset_domain[:1].upper() in "AEIOU" else "a"
    parts = [f"This looks like {article} **{dataset_domain}** dataset with **{len(data):,} records** "
             f"and **{len(df.columns)} columns**."]
    if date_col and data[date_col].notna().any():
        parts.append(f"It spans **{data[date_col].min():%d %b %Y}** to **{data[date_col].max():%d %b %Y}** "
                     f"(`{date_col}`).")
    if metric:
        value = data[metric].count() if agg == "count" else data[metric].agg(agg)
        parts.append(f"For the current selection, the {agg} of **{metric}** is **{fmt(value)}**.")
    parts.append(f"Data health score: **{health_score(data)}/100**.")
    return " ".join(parts)


# ---------- instant question answering (pandas, no AI needed) ----------

def _alts(word):
    alts = [word, word + "s", word + "es"]
    if word.endswith("y"):
        alts.append(word[:-1] + "ies")
    return alts


def word_in(q, word):
    return re.search(r"\b(?:" + "|".join(re.escape(a) for a in _alts(word)) + r")\b", q)


def find_mentions(q, cols):
    """Columns referred to in the question, in order of appearance."""
    hits = []
    for c in cols:
        base = norm(c).replace("_", " ")
        if not base:
            continue
        m = word_in(q, base)
        if not m:
            toks = [t for t in base.split() if t not in ("id", "no", "number")]
            if len(toks) > 1 and all(word_in(q, t) for t in toks):
                m = word_in(q, toks[0])
        if m:
            hits.append((m.start(), c))
    return [c for _, c in sorted(hits)]


def entity_label(col) -> str:
    base = re.sub(r"(?i)[_\s-]*(id|uuid|guid|no|number)$", "", str(col)).replace("_", " ").strip()
    base = (base or str(col)).title()
    return base if base.lower().endswith("s") else base + "s"


def answer_from_data(question, data):
    """Answer common analytics questions directly from the data. Returns dict or None."""
    try:
        return _answer_from_data(question, data)
    except Exception:
        return None


def _answer_from_data(question, data):
    q = question.lower().strip()
    if not q:
        return None

    if re.search(r"\b(summari[sz]e|summary|overview|describe|tell me about)\b", q):
        text = executive_summary(data)
        hl = auto_insights(data)[:5]
        if hl:
            text += "\n\n**Highlights**\n" + "\n".join(f"- {h}" for h in hl)
        return {"text": text}

    if re.search(r"\b(improve|recommend|recommendation|suggest|action|advice|next steps)\b", q):
        recs = recommendations(data)
        if recs:
            return {"text": "**Recommended actions**\n\n" + "\n".join(f"{i}. {r}" for i, r in enumerate(recs, 1))}

    mets = find_mentions(q, numeric_cols)
    for word, col in (("sales", revenue_col), ("revenue", revenue_col),
                      ("profit", profit_col), ("earnings", profit_col)):
        if col and col not in mets and word_in(q, word):
            mets.append(col)
    dims = [d for d in find_mentions(q, roles["dimensions"]) if d not in mets]

    # filters such as "... in Mumbai"
    scoped, scope_notes = data, []
    for c in roles["dimensions"]:
        if c in dims:
            continue
        for v in sorted(data[c].dropna().astype(str).unique(), key=len, reverse=True):
            if len(v) >= 3 and re.search(r"\b" + re.escape(v.lower()) + r"\b", q):
                scoped = scoped[scoped[c].astype(str) == v]
                scope_notes.append(f"{c} = {v}")
                break
    if scoped.empty:
        return {"text": "No records match that combination of filters."}
    scope = f" _(for {', '.join(scope_notes)})_" if scope_notes else ""

    agg_w = None
    if re.search(r"\b(average|avg|mean)\b", q):
        agg_w = "mean"
    elif re.search(r"\bmedian\b", q):
        agg_w = "median"
    elif re.search(r"\b(maximum|max)\b", q):
        agg_w = "max"
    elif re.search(r"\b(minimum|min)\b", q):
        agg_w = "min"
    elif re.search(r"\b(how many|count|number of)\b", q):
        agg_w = "count"
    elif re.search(r"\b(total|sum|overall)\b", q):
        agg_w = "sum"
    rank_desc = re.search(r"\b(highest|most|best|top|largest|biggest|leading|greatest)\b", q)
    rank_asc = re.search(r"\b(lowest|least|worst|bottom|smallest|weakest)\b", q)
    trend_w = re.search(r"\b(trend|trends|over time|monthly|by month|per month|growth|each month)\b", q)
    n_match = re.search(r"\b(?:top|bottom)\s+(\d+)\b", q)
    top_n = int(n_match.group(1)) if n_match else 5

    m = mets[0] if mets else metric

    # ---- trend over time
    if trend_w and date_col:
        how = agg_w or (default_agg(m) if m else "count")
        series = monthly_series(scoped, m if how != "count" else m, how) if m else None
        if series is None:
            series = scoped.groupby(pd.Grouper(key=date_col, freq="MS")).size()
            series = series if len(series) >= 2 else None
            how, m = "count", None
        if series is not None:
            name = m or "records"
            tbl = series.reset_index()
            tbl.columns = ["Month", name]
            text = (f"Monthly {how} of **{name}**: peak in **{series.idxmax():%b %Y}** ({fmt(series.max())}), "
                    f"lowest in **{series.idxmin():%b %Y}** ({fmt(series.min())}).")
            if series.iloc[-2] != 0:
                text += (f" The latest month is {(series.iloc[-1] - series.iloc[-2]) / abs(series.iloc[-2]) * 100:+.1f}% "
                         f"vs the one before.")
            fig = px.line(tbl, x="Month", y=name, markers=True, title=f"Monthly {how} of {name}")
            fig.update_traces(line=dict(color="#245A91", width=3))
            return {"text": text + scope, "table": tbl, "fig": fig}

    # ---- "which / top / best" without naming a column: use the first dimension
    assumed = None
    if not dims and (rank_desc or rank_asc) and roles["dimensions"]:
        dims = [roles["dimensions"][0]]
        assumed = dims[0]

    # ---- group-by answers
    if dims:
        d = dims[0]
        how = agg_w or (default_agg(m) if m else "count")
        g, val = aggregate(scoped, d, m, how)
        g = g.sort_values(val, ascending=bool(rank_asc and not rank_desc))
        shown = g.head(top_n)
        unit = "records" if val == "count" else val
        lead = g.iloc[0]
        total = g[val].sum()
        if n_match:
            word = "Bottom" if rank_asc and not rank_desc else "Top"
            text = (f"{word} {len(shown)} by {how} of {unit} ({d}): "
                    + ", ".join(f"**{r[d]}** ({fmt(r[val])})" for _, r in shown.iterrows()) + ".")
        elif rank_desc or rank_asc:
            word = "lowest" if rank_asc and not rank_desc else "highest"
            text = f"**{lead[d]}** has the {word} {how} of {unit}: **{fmt(lead[val])}**"
            if how in ("sum", "count") and total > 0:
                text += f" ({lead[val] / total * 100:.1f}% of the total)"
            text += "."
            if len(shown) > 1:
                text += " Next: " + ", ".join(f"{r[d]} ({fmt(r[val])})" for _, r in shown.iloc[1:4].iterrows()) + "."
        else:
            text = (f"{how.title()} of {unit} by {d}: "
                    + ", ".join(f"**{r[d]}** {fmt(r[val])}" for _, r in shown.head(3).iterrows()) + ".")
        if assumed:
            text += f"\n\n_I grouped by **{assumed}**. Name another column in your question to change that._"
        fig = px.bar(shown, x=d, y=val, text_auto=".2s", title=f"{how.title()} of {unit} by {d}",
                     color=val, color_continuous_scale=BLUE_SCALE)
        fig.update_coloraxes(showscale=False)
        return {"text": text + scope, "table": g.head(15), "fig": fig}

    # ---- single-number answers
    if mets and not agg_w and (scope_notes or len(q.split()) <= 6):
        agg_w = default_agg(mets[0])
    if agg_w:
        if agg_w == "count" or not mets:
            for idc in types["id"]:
                singular = entity_label(idc).lower().rstrip("s")
                if singular and singular in q and not mets:
                    return {"text": f"There are **{scoped[idc].nunique():,}** unique {entity_label(idc).lower()}." + scope}
            return {"text": f"There are **{len(scoped):,}** records." + scope}
        col = mets[0]
        value = scoped[col].agg(agg_w)
        word = {"sum": "total", "mean": "average", "median": "median", "max": "maximum", "min": "minimum"}[agg_w]
        return {"text": f"The {word} {col} is **{fmt(value)}**." + scope}

    return None


# ---------- AI prompt context ----------

def build_ai_context(data, max_chars) -> str:
    parts = [f"Rows: {len(data)}, Columns: {len(data.columns)}"]
    kinds = []
    for c in data.columns:
        kind = ("numeric" if c in types["numeric"] else "date" if c in types["datetime"]
                else "category" if c in types["categorical"] else "text/id")
        kinds.append(f"{c} ({kind})")
    parts.append("Columns: " + "; ".join(kinds))
    if date_col:
        parts.append(f"Date range ({date_col}): {data[date_col].min():%Y-%m-%d} to {data[date_col].max():%Y-%m-%d}")
    if numeric_cols:
        cols = numeric_cols[:8]
        desc = data[cols].describe().T[["mean", "min", "max"]].round(2)
        desc["sum"] = data[cols].sum().round(2)
        parts.append("Numeric summary:\n" + desc.to_string())
    for col in roles["dimensions"][:3]:
        grouped, val = aggregate(data, col, metric, agg)
        parts.append(f"{agg} of {metric or 'rows'} by {col} (top 8):\n"
                     + grouped.sort_values(val, ascending=False).head(8).round(2).to_string(index=False))
    trend = monthly_series(data, metric, agg)
    if trend is not None:
        parts.append(f"Monthly {agg} of {metric}:\n" + trend.tail(12).round(2).to_string())
    return "\n\n".join(parts)[:max_chars]


def list_ollama_models() -> list:
    if not OLLAMA_AVAILABLE:
        return []
    try:
        result = ollama.list()
        items = result["models"] if isinstance(result, dict) else getattr(result, "models", [])
        names = []
        for item in items:
            name = (item.get("model") or item.get("name")) if isinstance(item, dict) \
                else (getattr(item, "model", None) or getattr(item, "name", None))
            if name:
                names.append(name)
        return names
    except Exception:
        return []


def rec_card(icon, title, value, subtitle, color):
    st.markdown(
        f'<div class="rec-card" style="border-top:4px solid {color};">'
        f'<div style="font-size:23px;">{icon}</div>'
        f'<div style="color:#64748B;font-size:12px;font-weight:700;">{html.escape(title)}</div>'
        f'<div style="color:#173B65;font-size:19px;font-weight:750;margin-top:10px;">{html.escape(str(value))}</div>'
        f'<div style="color:#64748B;font-size:12px;margin-top:5px;">{html.escape(subtitle)}</div></div>',
        unsafe_allow_html=True)


# =========================================================
# 7. HERO + TABS
# =========================================================

chips = [f"📄 {len(fdf):,} rows", f"🧱 {len(df.columns)} columns", f"🧠 {dataset_domain}"]
if date_col:
    chips.append(f"📅 {fdf[date_col].min():%d %b %Y} → {fdf[date_col].max():%d %b %Y}")
chips.append(f"🩺 Health {health_score(df)}/100")
st.markdown(
    f'<div class="hero"><div class="hero-title">{html.escape(str(source_label))}</div>'
    f'<div class="hero-sub">Interactive analysis ready - use the sidebar to filter, then explore the tabs.</div>'
    + "".join(f'<span class="chip">{html.escape(c)}</span>' for c in chips) + "</div>",
    unsafe_allow_html=True)

tab_labels = ["📋 Overview", "📊 Auto Dashboard"]
if is_sales:
    tab_labels.append("💼 Business Deep Dive")
tab_labels += ["🛠️ Chart Builder", "🧪 Data Quality", "🤖 AI Assistant", "📥 Export"]
tabs = dict(zip(tab_labels, st.tabs(tab_labels)))


# ---------------------------------------------------------
# TAB: OVERVIEW
# ---------------------------------------------------------
with tabs["📋 Overview"]:
    st.caption(f"Source: **{source_label}**  |  Showing {len(fdf):,} of {len(df):,} rows after filters")
    st.markdown(executive_summary(fdf))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📄 Rows", f"{len(fdf):,}")
    c2.metric("🧱 Columns", f"{len(df.columns)}")
    c3.metric("🔢 Numeric / 🏷️ Category", f"{len(numeric_cols)} / {len(types['categorical'])}")
    c4.metric("❓ Missing Cells", f"{fdf.isna().mean().mean() * 100:.1f}%")

    st.markdown("## 📈 Key Metrics")
    kpis = []
    if is_sales:
        kpis.append((f"💰 Total {revenue_col}", fmt(fdf[revenue_col].sum())))
        if profit_col:
            kpis.append((f"📊 Total {profit_col}", fmt(fdf[profit_col].sum())))
        orders = fdf[order_col].nunique() if order_col else None
        if orders:
            kpis.append(("🛒 Total Orders", f"{orders:,}"))
        if qty_col:
            kpis.append((f"📦 Total {qty_col}", f"{fdf[qty_col].sum():,.0f}"))
        if orders:
            kpis.append(("🧾 Average Order Value", fmt(fdf[revenue_col].sum() / orders)))
        if profit_col and fdf[revenue_col].sum() != 0:
            kpis.append(("💹 Profit Margin", f"{fdf[profit_col].sum() / fdf[revenue_col].sum() * 100:.2f}%"))
    else:
        kpis.append(("📄 Total Records", f"{len(fdf):,}"))
        for c in [c for c in types["id"] if name_has(c, ("customer", "employee", "student", "product",
                                                          "order", "account", "user", "patient", "client", "member"))][:1]:
            kpis.append((f"👥 Unique {entity_label(c)}", f"{fdf[c].nunique(dropna=True):,}"))
        for col in roles["money"][:3]:
            total = default_agg(col) == "sum"
            value = fdf[col].sum(min_count=1) if total else fdf[col].mean()
            kpis.append((f"{'Total' if total else 'Average'} {col}", fmt(value)))
        for col in roles["quantity"][:1]:
            kpis.append((f"Total {col}", fmt(fdf[col].sum(min_count=1))))
        for col in roles["rating"][:2] + roles["age"][:1] + roles["percentage"][:1]:
            kpis.append((f"Average {col}", fmt(fdf[col].mean())))
        if len(kpis) <= 2:
            for col in roles["other_measures"][:4]:
                kpis.append((f"Average {col}", fmt(fdf[col].mean())))
    kpis = kpis[:9]
    for i in range(0, len(kpis), 3):
        for box, (label, value) in zip(st.columns(3), kpis[i:i + 3]):
            box.metric(label, value)

    st.markdown("## 🔎 Data Preview")
    show_table(fdf.head(100))

    st.markdown("## 🧬 Detected Column Types")
    st.caption("The app infers each column's role from its name and values. Review it for unusual headers.")
    role_of = {}
    for role in ("money", "quantity", "rating", "age", "percentage", "other_measures"):
        for c in roles[role]:
            role_of[c] = role.replace("_", " ").replace("other measures", "measure")
    type_rows = []
    for kind, label in [("numeric", "🔢 Numeric"), ("categorical", "🏷️ Category"), ("datetime", "📅 Date"),
                        ("id", "🆔 ID"), ("text", "📝 Text")]:
        for col in types[kind]:
            type_rows.append({"Column": col, "Detected As": label,
                              "Likely Meaning": role_of.get(col, "-") if kind == "numeric" else "-",
                              "Unique Values": df[col].nunique()})
    show_table(pd.DataFrame(type_rows))


# ---------------------------------------------------------
# TAB: AUTO DASHBOARD
# ---------------------------------------------------------
with tabs["📊 Auto Dashboard"]:
    st.markdown("## 💡 Smart Insights")
    insights = auto_insights(fdf)
    if insights:
        for line in insights:
            st.markdown(f"- {line}")
    else:
        st.info("Not enough structure in this data for automatic insights.")

    recs = recommendations(fdf)
    if recs:
        with st.expander("🎯 Recommended actions", expanded=True):
            for i, r in enumerate(recs, 1):
                st.markdown(f"{i}. {r}")
    st.divider()

    # ---- trend over time (+ optional forecast)
    if date_col:
        st.markdown("## 📅 Trend Over Time")
        t1, t2 = st.columns([3, 2])
        grain = t1.radio("Group by", ["Day", "Week", "Month", "Quarter"], index=2, horizontal=True)
        show_fc = t2.checkbox("Show simple linear forecast (next 3 periods)", value=False)
        rule = {"Day": "D", "Week": "W", "Month": "MS", "Quarter": "QS"}[grain]
        if metric and agg != "count":
            trend = fdf.groupby(pd.Grouper(key=date_col, freq=rule))[metric].agg(agg).reset_index()
            y_name = metric
        else:
            trend = fdf.groupby(pd.Grouper(key=date_col, freq=rule)).size().reset_index(name="count")
            y_name = "count"
        fig = px.line(trend, x=date_col, y=y_name, markers=True, title=f"{agg.title()} of {y_name} by {grain}")
        fig.update_traces(line=dict(color="#245A91", width=3), marker=dict(size=7), name="Actual")
        if show_fc:
            clean = trend.dropna()
            if len(clean) >= 4:
                xs = np.arange(len(clean))
                slope, intercept = np.polyfit(xs, clean[y_name].astype(float).values, 1)
                future_x = np.arange(len(clean), len(clean) + 3)
                future_dates = pd.date_range(clean[date_col].iloc[-1], periods=4, freq=rule)[1:]
                fig.add_scatter(x=future_dates, y=intercept + slope * future_x, mode="lines+markers",
                                name="Forecast", line=dict(color="#D99A37", width=3, dash="dash"))
                st.caption("Forecast is a straight-line projection of the trend - indicative only.")
            else:
                st.caption("Need at least 4 periods to forecast.")
        show_chart(fig)

    # ---- Pareto
    if agg in ("sum", "count") and metric and roles["dimensions"]:
        st.markdown("## 🏆 Pareto (80/20) Analysis")
        pdim = st.selectbox("Analyse contribution by", roles["dimensions"], key="pareto_dim")
        pg, pval = aggregate(fdf, pdim, metric, agg)
        pg = pg.sort_values(pval, ascending=False)
        ptotal = pg[pval].sum()
        if len(pg) >= 3 and ptotal > 0:
            pg["cum"] = pg[pval].cumsum() / ptotal * 100
            n80 = int((pg["cum"] < 80).sum() + 1)
            shown = pg.head(20)
            pf = go.Figure()
            pf.add_bar(x=shown[pdim].astype(str), y=shown[pval], name=pval, marker_color="#245A91")
            pf.add_scatter(x=shown[pdim].astype(str), y=shown["cum"], name="Cumulative %", yaxis="y2",
                           mode="lines+markers", line=dict(color="#D99A37", width=3))
            pf.update_layout(title=f"{n80} of {len(pg)} {pdim} values make up 80% of {pval}",
                             yaxis2=dict(overlaying="y", side="right", range=[0, 105], title="Cumulative %"),
                             legend=dict(orientation="h", y=1.12))
            show_chart(pf)

    # ---- category breakdowns
    if roles["dimensions"]:
        st.markdown("## 🏷️ Category Breakdown")
        b1, b2, b3 = st.columns([3, 1, 1])
        cats = b1.multiselect("Columns to break down", roles["dimensions"],
                              default=roles["dimensions"][:4], key=f"breakdown_{dsk}")
        top_n = b2.slider("Top N", 3, 20, 10)
        style = b3.radio("Style", ["Bar", "Pie"], horizontal=True)
        for i in range(0, len(cats), 2):
            for box, col in zip(st.columns(2), cats[i:i + 2]):
                with box:
                    grouped, val = aggregate(fdf, col, metric, agg)
                    grouped = grouped.sort_values(val, ascending=False).head(top_n)
                    title = f"{agg.title()} of {val} by {col}"
                    if style == "Pie":
                        fig = px.pie(grouped, names=col, values=val, hole=0.45, title=title,
                                     color_discrete_sequence=PALETTE)
                        fig.update_traces(textposition="inside", textinfo="percent+label")
                    else:
                        fig = px.bar(grouped, x=col, y=val, title=title, text_auto=".2s",
                                     color=val, color_continuous_scale=BLUE_SCALE)
                        fig.update_coloraxes(showscale=False)
                        fig.update_traces(textposition="outside")
                    show_chart(fig)

    # ---- cross analysis heatmap
    if len(roles["dimensions"]) >= 2:
        st.markdown("## 🔀 Cross Analysis")
        x1, x2 = st.columns(2)
        dim_a = x1.selectbox("Rows", roles["dimensions"], index=0, key="cross_a")
        dim_b = x2.selectbox("Columns", roles["dimensions"], index=1, key="cross_b")
        if dim_a != dim_b:
            cg, cval = aggregate(fdf, [dim_a, dim_b], metric, agg)
            top_a = cg.groupby(dim_a)[cval].sum().nlargest(15).index
            top_b = cg.groupby(dim_b)[cval].sum().nlargest(15).index
            cg = cg[cg[dim_a].isin(top_a) & cg[dim_b].isin(top_b)]
            pivot = cg.pivot(index=dim_a, columns=dim_b, values=cval)
            fig = px.imshow(pivot, text_auto=".2s", aspect="auto", color_continuous_scale=BLUE_SCALE,
                            title=f"{agg.title()} of {cval}: {dim_a} x {dim_b}")
            show_chart(fig)
        else:
            st.info("Pick two different columns.")

    # ---- distributions
    if numeric_cols:
        st.markdown("## 📦 Distributions")
        suggested = roles["money"][:2] + roles["rating"][:1] + roles["age"][:1]
        if not suggested:
            suggested = roles["other_measures"][:3] + roles["quantity"][:1]
        nums = st.multiselect("Numeric columns to explore", numeric_cols,
                              default=list(dict.fromkeys(suggested))[:4], key=f"dist_{dsk}")
        for i in range(0, len(nums), 2):
            for box, col in zip(st.columns(2), nums[i:i + 2]):
                with box:
                    fig = px.histogram(fdf, x=col, nbins=30, marginal="box", title=f"Distribution of {col}",
                                       color_discrete_sequence=["#245A91"])
                    show_chart(fig)

    # ---- correlation
    if len(numeric_cols) >= 2:
        st.markdown("## 🔗 Correlation Heatmap")
        corr = fdf[numeric_cols[:20]].corr()
        fig = px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1,
                        title="How numeric columns relate to each other")
        show_chart(fig)


# ---------------------------------------------------------
# TAB: BUSINESS DEEP DIVE (only for sales-like data)
# ---------------------------------------------------------
if is_sales:
    with tabs["💼 Business Deep Dive"]:
        loc_dim = find_col(roles["dimensions"], ["city", "location", "region", "state", "country"])
        prod_dim = find_col(roles["dimensions"], ["product", "item", "service", "sku"])
        cat_dim = find_col([c for c in roles["dimensions"] if c != prod_dim],
                           ["category", "department", "segment", "type"])
        val_col = profit_col or revenue_col

        if loc_dim:
            st.markdown(f"## 🌆 Performance by {loc_dim}")
            l1, l2 = st.columns(2)
            with l1:
                d = fdf.groupby(loc_dim)[revenue_col].sum().reset_index().sort_values(revenue_col, ascending=False)
                fig = px.bar(d, x=loc_dim, y=revenue_col, title=f"{revenue_col} by {loc_dim}", text_auto=".2s",
                             color=revenue_col, color_continuous_scale=BLUE_SCALE)
                fig.update_coloraxes(showscale=False)
                fig.update_traces(textposition="outside")
                show_chart(fig)
            if profit_col:
                with l2:
                    d = fdf.groupby(loc_dim)[profit_col].sum().reset_index().sort_values(profit_col, ascending=False)
                    fig = px.bar(d, x=loc_dim, y=profit_col, title=f"{profit_col} by {loc_dim}", text_auto=".2s",
                                 color=profit_col, color_continuous_scale=GREEN_SCALE)
                    fig.update_coloraxes(showscale=False)
                    fig.update_traces(textposition="outside")
                    show_chart(fig)

        if date_col:
            st.markdown("## 📅 Monthly Trends")
            m1, m2 = st.columns(2)
            with m1:
                d = fdf.groupby(pd.Grouper(key=date_col, freq="MS"))[revenue_col].sum().reset_index()
                fig = px.line(d, x=date_col, y=revenue_col, markers=True, title=f"Monthly {revenue_col}")
                fig.update_traces(line=dict(color="#245A91", width=3), marker=dict(size=8))
                show_chart(fig)
            if profit_col:
                with m2:
                    d = fdf.groupby(pd.Grouper(key=date_col, freq="MS"))[profit_col].sum().reset_index()
                    fig = px.line(d, x=date_col, y=profit_col, markers=True, title=f"Monthly {profit_col}")
                    fig.update_traces(line=dict(color="#23866B", width=3), marker=dict(size=8))
                    show_chart(fig)

        if prod_dim:
            st.markdown(f"## 📦 {prod_dim} Performance")
            spec = {"Revenue": (revenue_col, "sum")}
            if profit_col:
                spec["Profit"] = (profit_col, "sum")
            if qty_col:
                spec["Quantity"] = (qty_col, "sum")
            ps = fdf.groupby(prod_dim).agg(**spec).reset_index().sort_values("Revenue", ascending=False)
            if profit_col:
                ps["Profit Margin (%)"] = np.where(ps["Revenue"] != 0, ps["Profit"] / ps["Revenue"] * 100, 0)
            p1, p2 = st.columns(2)
            with p1:
                fig = px.bar(ps.head(15), x=prod_dim, y="Revenue", text_auto=".2s",
                             title=f"Top {prod_dim} by {revenue_col}",
                             color="Revenue", color_continuous_scale=BLUE_SCALE)
                fig.update_coloraxes(showscale=False)
                fig.update_traces(textposition="outside")
                show_chart(fig)
            with p2:
                if cat_dim:
                    cd = fdf.groupby(cat_dim)[revenue_col].sum().reset_index()
                    fig = px.pie(cd, names=cat_dim, values=revenue_col, hole=0.48, color_discrete_sequence=PALETTE,
                                 title=f"{revenue_col} share by {cat_dim}")
                    fig.update_traces(textposition="inside", textinfo="percent+label")
                    show_chart(fig)
            st.markdown("### 🔍 Product Profitability (lowest margin first)")
            show_table(ps.sort_values("Profit Margin (%)") if profit_col else ps)
            if profit_col:
                st.caption("Products with lower profit margins may need pricing or cost review.")

        st.markdown("## 🎯 Business Recommendations")
        r1, r2, r3 = st.columns(3, gap="medium")
        if loc_dim:
            best = fdf.groupby(loc_dim)[val_col].sum().idxmax()
            with r1:
                rec_card("🏙️", "BEST PERFORMING " + loc_dim.upper(), best, f"Highest total {val_col}", "#245A91")
        if cat_dim or prod_dim:
            dim = cat_dim or prod_dim
            best_cat = fdf.groupby(dim)[revenue_col].sum().idxmax()
            with r2:
                rec_card("📈", "TOP REVENUE " + dim.upper(), best_cat, f"Highest total {revenue_col}", "#23866B")
        if prod_dim:
            worst = fdf.groupby(prod_dim)[val_col].sum().idxmin()
            with r3:
                rec_card("⚠️", f"{prod_dim.upper()} TO REVIEW", worst, f"Lowest total {val_col}", "#D99A37")


# ---------------------------------------------------------
# TAB: CHART BUILDER
# ---------------------------------------------------------
with tabs["🛠️ Chart Builder"]:
    st.markdown("## 🛠️ Build Your Own Chart")
    c1, c2, c3, c4 = st.columns(4)
    chart_type = c1.selectbox("Chart type", ["Bar", "Line", "Area", "Scatter", "Histogram", "Box", "Pie", "Treemap"])
    x_options = list(dict.fromkeys(types["categorical"] + types["datetime"] + numeric_cols)) or all_cols
    x = c2.selectbox("X axis / group", x_options)
    y_choice = c3.selectbox("Y axis (value)", ["(none)"] + numeric_cols)
    color_choice = c4.selectbox("Color by", ["(none)"] + types["categorical"])

    c5, c6, c7 = st.columns(3)
    b_agg = c5.selectbox("Aggregation", AGG_OPTIONS, key="b_agg")
    b_top = c6.slider("Top N (categories)", 3, 30, 10, key="b_top")
    b_bins = c7.slider("Histogram bins", 5, 100, 30, key="b_bins")

    y = None if y_choice == "(none)" else y_choice
    color = None if color_choice in ("(none)", x) else color_choice

    plot_df = fdf.copy()
    x_col = x
    if x in types["datetime"]:
        g = st.radio("Time grain", ["Day", "Week", "Month", "Quarter"], index=2, horizontal=True, key="b_grain")
        code = {"Day": "D", "Week": "W", "Month": "M", "Quarter": "Q"}[g]
        plot_df["_x"] = plot_df[x].dt.to_period(code).dt.to_timestamp()
        x_col = "_x"

    try:
        fig = None
        if chart_type in ("Bar", "Line", "Area"):
            by = [x_col] + ([color] if color else [])
            data, val = aggregate(plot_df, by, y, b_agg)
            categorical_x = x not in types["datetime"] and x not in numeric_cols
            if categorical_x:
                keep = data.groupby(x_col)[val].sum().sort_values(ascending=False).head(b_top).index
                data = data[data[x_col].isin(keep)]
            if chart_type == "Bar" and categorical_x:
                data = data.sort_values(val, ascending=False)
            else:
                data = data.sort_values(x_col)
            title = f"{b_agg.title()} of {val} by {x}"
            if chart_type == "Bar":
                fig = px.bar(data, x=x_col, y=val, color=color, title=title, barmode="group",
                             color_discrete_sequence=PALETTE)
            elif chart_type == "Line":
                fig = px.line(data, x=x_col, y=val, color=color, markers=True, title=title,
                              color_discrete_sequence=PALETTE)
            else:
                fig = px.area(data, x=x_col, y=val, color=color, title=title, color_discrete_sequence=PALETTE)
            fig.update_xaxes(title=x)
        elif chart_type == "Scatter":
            if y is None:
                st.warning("Pick a numeric Y axis for a scatter plot.")
            else:
                sample = plot_df.sample(min(len(plot_df), 5000), random_state=1)
                fig = px.scatter(sample, x=x_col, y=y, color=color, opacity=0.7, title=f"{y} vs {x}",
                                 color_discrete_sequence=PALETTE)
        elif chart_type == "Histogram":
            fig = px.histogram(plot_df, x=x_col, color=color, nbins=b_bins, title=f"Distribution of {x}",
                               color_discrete_sequence=PALETTE)
        elif chart_type == "Box":
            if y:
                fig = px.box(plot_df, x=x_col, y=y, color=color, title=f"{y} by {x}", color_discrete_sequence=PALETTE)
            elif x in numeric_cols:
                fig = px.box(plot_df, y=x_col, color=color, title=f"Spread of {x}", color_discrete_sequence=PALETTE)
            else:
                st.warning("Pick a numeric Y axis (or a numeric X) for a box plot.")
        elif chart_type in ("Pie", "Treemap"):
            data, val = aggregate(plot_df, [x_col], y, b_agg)
            data = data.sort_values(val, ascending=False).head(b_top)
            data = data[data[val] > 0]
            title = f"{b_agg.title()} of {val} by {x}"
            if chart_type == "Pie":
                fig = px.pie(data, names=x_col, values=val, hole=0.4, title=title, color_discrete_sequence=PALETTE)
                fig.update_traces(textposition="inside", textinfo="percent+label")
            else:
                data[x_col] = data[x_col].astype(str)
                fig = px.treemap(data, path=[x_col], values=val, title=title, color=val,
                                 color_continuous_scale=BLUE_SCALE)
                fig.update_coloraxes(showscale=False)
        if fig is not None:
            show_chart(fig)
    except Exception as exc:
        st.error(f"Could not draw this chart with the selected columns: {exc}")


# ---------------------------------------------------------
# TAB: DATA QUALITY
# ---------------------------------------------------------
with tabs["🧪 Data Quality"]:
    st.markdown("## 🧪 Data Quality Report")
    score = health_score(df)
    g1, g2 = st.columns([1, 2])
    with g1:
        color = "#23866B" if score >= 85 else "#D99A37" if score >= 65 else "#C0392B"
        gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=score, title={"text": "Data Health Score"},
            gauge={"axis": {"range": [0, 100]}, "bar": {"color": color},
                   "steps": [{"range": [0, 65], "color": "#FBE4E1"}, {"range": [65, 85], "color": "#FCF1DC"},
                             {"range": [85, 100], "color": "#DDF2EA"}]}))
        gauge.update_layout(height=260)
        show_chart(gauge)
    with g2:
        q1, q2, q3 = st.columns(3)
        q1.metric("🔁 Duplicate Rows", f"{int(df.duplicated().sum()):,}")
        q2.metric("❓ Columns With Gaps", f"{int((df.isna().sum() > 0).sum())}")
        q3.metric("🧱 Total Cells", f"{df.size:,}")
        st.caption("Score starts at 100 and loses points for missing values, duplicate rows and extreme outliers.")

    missing = pd.DataFrame({
        "Column": df.columns, "Missing": df.isna().sum().values,
        "Missing %": (df.isna().mean() * 100).round(2).values,
        "Unique": [df[c].nunique() for c in df.columns],
        "Example": [str(df[c].dropna().iloc[0]) if df[c].notna().any() else "-" for c in df.columns]})
    show_table(missing)

    gaps = missing[missing["Missing"] > 0].sort_values("Missing %", ascending=False)
    if not gaps.empty:
        fig = px.bar(gaps, x="Column", y="Missing %", title="Missing Values by Column",
                     color="Missing %", color_continuous_scale=["#F6D9A8", "#D99A37"])
        fig.update_coloraxes(showscale=False)
        show_chart(fig)
    else:
        st.success("No missing values found.")

    ot = outlier_table(df)
    if not ot.empty:
        st.markdown("### 🚨 Outlier Detection (IQR method)")
        show_table(ot.sort_values("Outlier %", ascending=False))

    if conversion_notes:
        with st.expander("🔧 Automatic conversions applied"):
            for note in conversion_notes:
                st.markdown(f"- {note}")
    if numeric_cols:
        with st.expander("📐 Statistical summary (numeric columns)"):
            st.dataframe(fdf[numeric_cols].describe().T.round(2))


# ---------------------------------------------------------
# TAB: AI ASSISTANT
# ---------------------------------------------------------
AI_MODES = {
    "Low memory (best for 1B models)": (1024, 1500, 220, 2),
    "Balanced": (2048, 3500, 400, 4),
    "Detailed (needs more RAM)": (4096, 6500, 700, 6),
}


def render_message(msg):
    st.markdown(msg["content"])
    if msg.get("table") is not None:
        with st.expander("View table"):
            show_table(msg["table"])
    if msg.get("fig") is not None:
        show_chart(msg["fig"])


with tabs["🤖 AI Assistant"]:
    st.markdown("## 🤖 AI Business Assistant")
    st.caption("⚡ Most questions are answered instantly from your data. The local AI model handles the rest.")

    s1, s2, s3 = st.columns([2, 2, 2])
    installed = list_ollama_models()
    if installed:
        pref = "llama3.2:1b" if "llama3.2:1b" in installed else installed[0]
        model_name = s1.selectbox("Ollama model", installed, index=installed.index(pref))
    else:
        model_name = s1.text_input("Ollama model", value="llama3.2:1b")
    mode_name = s2.selectbox("AI memory mode", list(AI_MODES))
    num_ctx, ctx_chars, num_predict, hist_n = AI_MODES[mode_name]
    use_llm = s3.checkbox("Use AI for questions I can't answer instantly", value=True)

    if not OLLAMA_AVAILABLE:
        st.warning("The `ollama` package is not installed (pip install ollama). Instant answers still work.")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    left, right = st.columns([6, 1])
    quick = None
    with left:
        st.markdown("**Try one:**")
        examples = ["Summarize this dataset", "What are the key trends?", "What should I improve?",
                    "Who are the top performers?"]
        for box, text in zip(st.columns(len(examples)), examples):
            if box.button(text, key=f"quick_{text}"):
                quick = text
        if roles["dimensions"] and metric:
            st.caption(f"You can also type things like: *\"{metric} by {roles['dimensions'][0]}\"*, "
                       f"*\"average {metric}\"*, *\"lowest {metric} {roles['dimensions'][0]}\"*, "
                       f"*\"top 3 {roles['dimensions'][0]} by {metric}\"*.")
    with right:
        if st.button("🗑️ Clear"):
            st.session_state.chat_history = []
            st.rerun()

    chat_box = st.container()
    with chat_box:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                render_message(message)

    typed = st.chat_input("Ask a question about your data...")
    question = typed or quick

    if question:
        with chat_box:
            with st.chat_message("user"):
                st.markdown(question)
            with st.chat_message("assistant"):
                result = answer_from_data(question, fdf)
                if result:
                    st.caption("⚡ Instant answer calculated directly from your data")
                    reply = {"role": "assistant", "content": result["text"],
                             "table": result.get("table"), "fig": result.get("fig")}
                    render_message(reply)
                    st.session_state.chat_history.append({"role": "user", "content": question})
                    st.session_state.chat_history.append(reply)
                elif not use_llm:
                    st.info("I couldn't answer that instantly. Try naming a column, e.g. "
                            "\"total revenue by city\", or enable AI above.")
                elif not OLLAMA_AVAILABLE:
                    st.error("Install the ollama package to use AI answers.")
                else:
                    system_prompt = (
                        "You are a professional Business Data Analyst. Answer ONLY from the data summary "
                        "below. Never invent numbers. If the answer is not in the summary, say so. "
                        "Use simple English, short paragraphs and practical recommendations.\n\n"
                        f"DATA SUMMARY:\n{build_ai_context(fdf, ctx_chars)}")
                    past = [{"role": m["role"], "content": m["content"]}
                            for m in st.session_state.chat_history[-hist_n:]]
                    messages = [{"role": "system", "content": system_prompt}] + past \
                        + [{"role": "user", "content": question}]
                    try:
                        with st.spinner("AI is analyzing your data..."):
                            res = ollama.chat(model=model_name, messages=messages,
                                              options={"num_ctx": num_ctx, "num_predict": num_predict,
                                                       "temperature": 0.2})
                        answer = res["message"]["content"]
                        st.markdown(answer)
                        st.session_state.chat_history.append({"role": "user", "content": question})
                        st.session_state.chat_history.append({"role": "assistant", "content": answer})
                    except Exception as exc:
                        text = str(exc).lower()
                        if any(k in text for k in ("allocate", "memory", "terminated", "status code: 500")):
                            st.error("The model could not load - your computer is low on free RAM.\n\n"
                                     "1. Close heavy apps and extra browser tabs.\n"
                                     "2. Choose **Low memory** mode above, or run `ollama pull llama3.2:1b`.\n"
                                     "3. Restart Ollama from the system tray.")
                        else:
                            st.error(f"AI connection error: {exc}\n\nMake sure Ollama is running and the model "
                                     f"is installed (`ollama pull {model_name}`).")
                        st.markdown("**Meanwhile, here is what the data shows (no AI needed):**")
                        for line in auto_insights(fdf)[:6]:
                            st.markdown(f"- {line}")


# ---------------------------------------------------------
# TAB: EXPORT
# ---------------------------------------------------------
with tabs["📥 Export"]:
    st.markdown("## 📥 Download")
    e1, e2, e3, e4 = st.columns(4)
    e1.download_button("⬇️ Filtered data (CSV)", data=fdf.to_csv(index=False).encode("utf-8"),
                       file_name="filtered_data.csv", mime="text/csv")
    e2.download_button("⬇️ Cleaned full data (CSV)", data=df.to_csv(index=False).encode("utf-8"),
                       file_name="cleaned_data.csv", mime="text/csv")

    report_lines = [f"# Data Insights Report - {source_label}", "", executive_summary(fdf).replace("**", ""), "",
                    "## Insights", *[f"- {i.replace('**', '')}" for i in auto_insights(fdf)], "",
                    "## Recommended actions", *[f"{n}. {r.replace('**', '')}" for n, r in enumerate(recommendations(fdf), 1)]]
    e3.download_button("⬇️ Insights report (Markdown)", data="\n".join(report_lines).encode("utf-8"),
                       file_name="insights_report.md", mime="text/markdown")

    if len(fdf) <= 50000:
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                fdf.to_excel(writer, sheet_name="Filtered Data", index=False)
                if numeric_cols:
                    fdf[numeric_cols].describe().T.round(2).to_excel(writer, sheet_name="Statistics")
                pd.DataFrame({"Insights": [i.replace("**", "") for i in auto_insights(fdf)]}) \
                    .to_excel(writer, sheet_name="Insights", index=False)
            e4.download_button("⬇️ Excel report (.xlsx)", data=buffer.getvalue(), file_name="analysis_report.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception:
            e4.caption("Install `openpyxl` for Excel export.")
    else:
        e4.caption("Excel export is skipped for very large selections.")


# =========================================================
# 8. FOOTER
# =========================================================

st.divider()
st.markdown("""
<div class="footer">
    <strong>AI Business Analyst Assistant</strong><br>
    Developed by Varshitha H V
</div>
""", unsafe_allow_html=True)
