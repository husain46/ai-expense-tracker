"""
AI Smart Expense Tracker
-------------------------
Pipeline: Receipt image -> Tesseract OCR -> Gemini (structures into JSON)
          -> SQLite storage -> Streamlit dashboard

Extra AI features (added on top of the basic idea):
1. Natural-language query box  (plain English -> SQL -> answer, via Gemini)
2. AI Budget Advisor           (Gemini gives a personalized saving tip if over budget)

Run with:  streamlit run app.py
"""

import os
import re
import json
import sqlite3
from datetime import datetime

import streamlit as st
import pandas as pd
from PIL import Image
import pytesseract
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
pytesseract.pytesseract.tesseract_cmd = r"D:\Tesseract-OCR\tesseract.exe"

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONTHLY_BUDGET = float(os.getenv("MONTHLY_BUDGET", 10000))

if GEMINI_API_KEY and GEMINI_API_KEY != "your_api_key_here":
    genai.configure(api_key=GEMINI_API_KEY)
    AI_READY = True
else:
    AI_READY = False

st.set_page_config(page_title="AI Smart Expense Tracker", page_icon="💳", layout="wide")

DB_FILE = "database/expenses.db"


def get_conn():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    return sqlite3.connect(DB_FILE)


def init_db():
    conn = get_conn()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            vendor TEXT,
            category TEXT,
            amount REAL,
            raw_text TEXT
        )"""
    )
    conn.commit()
    conn.close()


init_db()

# ---------------------------------------------------------------------------
# AI Step 1: OCR + Gemini structuring
# ---------------------------------------------------------------------------
def extract_text_from_image(image: Image.Image) -> str:
    """Real OCR using Tesseract. Requires the Tesseract binary installed on the OS."""
    return pytesseract.image_to_string(image)


def structure_receipt_with_ai(raw_text: str) -> dict:
    """Send raw, messy OCR text to Gemini and get back clean structured JSON."""
    if not AI_READY:
        return {"Date": datetime.now().strftime("%Y-%m-%d"), "Vendor": "Unknown",
                 "Category": "Misc", "Amount": 0.0}

    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    You are reading raw OCR text extracted from a shopping receipt photo.
    The text may contain spelling mistakes and broken line breaks caused by OCR errors.

    Extract these fields and return ONLY valid JSON, no markdown fences, no explanation:
    - "Date": in YYYY-MM-DD format (use today's date if not found)
    - "Vendor": store/business name
    - "Category": one of [Groceries, Food, Travel, Shopping, Bills, Entertainment, Misc]
    - "Amount": the final total paid, as a plain number (no currency symbol)

    Raw OCR text:
    {raw_text}
    """
    try:
        response = model.generate_content(prompt)
    except ResourceExhausted:
        st.warning("API quota reached for today. Please try again tomorrow or use a different API key. Your data is safe and the dashboard still works.")
        return None
    cleaned = re.sub(r"^```[a-zA-Z]*\n?|```$", "", response.text.strip()).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"Date": datetime.now().strftime("%Y-%m-%d"), "Vendor": "Unknown",
                 "Category": "Misc", "Amount": 0.0}


# ---------------------------------------------------------------------------
# AI Step 2 (NEW FEATURE): Natural language -> SQL -> answer
# ---------------------------------------------------------------------------
def answer_natural_language_query(question: str, schema_hint: str) -> str:
    if not AI_READY:
        return "AI is not configured. Please set GEMINI_API_KEY in your .env file."

    model = genai.GenerativeModel("gemini-2.5-flash")

    sql_prompt = f"""
    You write SQLite queries. The table is called 'entries' with columns:
    {schema_hint}

    Write ONE valid SQLite SELECT query (no explanation, no markdown) that answers:
    "{question}"
    Only return the raw SQL.
    """
    try:
        sql_response = model.generate_content(sql_prompt)
    except ResourceExhausted:
        st.warning("API quota reached for today. Please try again tomorrow or use a different API key. Your data is safe and the dashboard still works.")
        return ""
    sql_query = re.sub(r"^```[a-zA-Z]*\n?|```$", "", sql_response.text.strip()).strip()

    try:
        conn = get_conn()
        result_df = pd.read_sql_query(sql_query, conn)
        conn.close()
    except Exception as e:
        return f"Couldn't run that query safely ({e}). Try rephrasing your question."

    if result_df.empty:
        return "No matching records found."

    # Ask Gemini to phrase the raw query result as a friendly sentence
    answer_prompt = f"""
    The user asked: "{question}"
    The database returned this result table:
    {result_df.to_string(index=False)}

    Answer the user's question in one short, friendly sentence using this data.
    """
    try:
        final = model.generate_content(answer_prompt)
    except ResourceExhausted:
        st.warning("API quota reached for today. Please try again tomorrow or use a different API key. Your data is safe and the dashboard still works.")
        return ""
    return final.text.strip()


# ---------------------------------------------------------------------------
# AI Step 3 (NEW FEATURE): Budget advisor
# ---------------------------------------------------------------------------
def get_budget_advice(category_totals: pd.Series, total_spent: float, budget: float) -> str:
    if not AI_READY:
        return "Set GEMINI_API_KEY to enable AI budget tips."

    model = genai.GenerativeModel("gemini-2.5-flash")
    prompt = f"""
    A student's monthly budget is INR {budget}. They have spent INR {total_spent} so far.
    Category-wise breakdown: {category_totals.to_dict()}

    In 2-3 short sentences, give one specific, practical saving tip based on
    their highest spending category. Be encouraging, not preachy.
    """
    try:
        response = model.generate_content(prompt)
    except ResourceExhausted:
        st.warning("API quota reached for today. Please try again tomorrow or use a different API key. Your data is safe and the dashboard still works.")
        return ""
    return response.text.strip()


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.title("💳 AI Smart Expense Tracker")
st.caption("OCR + Gemini receipt parsing, SQLite storage, natural-language queries, and AI budget tips.")

if not AI_READY:
    st.warning("⚠️ GEMINI_API_KEY not set in .env — running in fallback mode. AI features are disabled until you add a key.")

tab1, tab2, tab3 = st.tabs(["📥 Add Receipt", "📊 Dashboard", "💬 Ask Your Data"])

# --- Tab 1: Upload & process receipt ---
with tab1:
    uploaded_image = st.file_uploader("Upload a receipt photo", type=["jpg", "jpeg", "png"])

    if uploaded_image:
        image = Image.open(uploaded_image)
        col1, col2 = st.columns(2)
        col1.image(image, caption="Uploaded receipt", use_column_width=True)

        if col1.button("⚡ Extract & Save with AI"):
            with st.spinner("Running OCR..."):
                try:
                    raw_text = extract_text_from_image(image)
                except Exception as e:
                    st.error(f"OCR failed — is Tesseract installed on this machine? ({e})")
                    raw_text = ""

            if raw_text.strip():
                with st.spinner("Structuring with Gemini..."):
                    data = structure_receipt_with_ai(raw_text)

                if data is not None:
                    conn = get_conn()
                    conn.execute(
                        "INSERT INTO entries (date, vendor, category, amount, raw_text) VALUES (?, ?, ?, ?, ?)",
                        (data.get("Date"), data.get("Vendor"), data.get("Category"),
                         float(data.get("Amount", 0)), raw_text),
                    )
                    conn.commit()
                    conn.close()

                    col2.success("Saved!")
                    col2.json(data)
            else:
                col2.error("No text could be read from this image.")

# --- Tab 2: Dashboard ---
with tab2:
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM entries ORDER BY id DESC", conn)
    conn.close()

    if df.empty:
        st.info("No expenses logged yet. Add a receipt in the first tab.")
    else:
        total_spent = df["amount"].sum()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Spent", f"₹ {total_spent:,.2f}")
        col2.metric("Monthly Budget", f"₹ {MONTHLY_BUDGET:,.2f}")
        col3.metric("Remaining", f"₹ {MONTHLY_BUDGET - total_spent:,.2f}")

        category_totals = df.groupby("category")["amount"].sum()

        st.subheader("Spending by Category")
        st.bar_chart(category_totals)

        st.subheader("AI Budget Advisor")
        if total_spent > MONTHLY_BUDGET:
            st.warning("You're over budget this month.")
        if st.button("Get AI saving tip"):
            with st.spinner("Thinking..."):
                tip = get_budget_advice(category_totals, total_spent, MONTHLY_BUDGET)
            if tip:
                st.info(tip)

        st.subheader("All Records")
        st.dataframe(df[["date", "vendor", "category", "amount"]], use_container_width=True)

# --- Tab 3: Natural language query ---
with tab3:
    st.write("Ask a question about your spending in plain English.")
    question = st.text_input("e.g. How much did I spend on groceries this month?")
    if st.button("Ask") and question:
        with st.spinner("Looking it up..."):
            answer = answer_natural_language_query(
                question,
                schema_hint="date (text), vendor (text), category (text), amount (real)",
            )
        if answer:
            st.success(answer)
