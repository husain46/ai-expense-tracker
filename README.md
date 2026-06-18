# AI Smart Expense Tracker

A diploma-level AI project: upload a photo of a receipt, and the app reads it (OCR),
understands it (Gemini LLM), saves it (SQLite), and lets you explore your spending
through a dashboard and plain-English questions.

## Pipeline (this is your one-line answer for viva)
**Receipt image → Tesseract OCR (text) → Gemini (structured JSON) → SQLite → Dashboard / NL queries**

## What makes this more than a basic OCR app
1. **Natural-language query box** — type a question like "how much did I spend on
   food in May?" and Gemini converts it to a SQL query, runs it, and answers in
   plain English (NL-to-SQL).
2. **AI Budget Advisor** — compares your spend to a budget and asks Gemini to
   generate a personalized saving tip based on your actual category breakdown.

These two are good talking points for your "what did you add beyond the existing
idea" question in viva.

## Setup (do this in VS Code's terminal)

### 1. Install Tesseract OCR (the actual OCR engine, not just the Python wrapper)
- **Windows:** download installer from https://github.com/UB-Mannheim/tesseract/wiki
  and add it to your PATH.
- **Mac:** `brew install tesseract`
- **Linux:** `sudo apt install tesseract-ocr`

### 2. Create a virtual environment and install dependencies
```bash
cd expense_tracker
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
```

### 3. Get a free Gemini API key
Go to https://aistudio.google.com/app/apikey, create a key, then:
```bash
cp .env.example .env
```
Open `.env` and paste your real key in place of `your_api_key_here`.

### 4. Run it
```bash
streamlit run app.py
```
It'll open in your browser at `http://localhost:8501`.

## Project structure
```
expense_tracker/
├── app.py              # Everything: OCR, AI parsing, DB, dashboard, NL queries
├── requirements.txt    # Python dependencies
├── .env.example         # Template for your API key (copy to .env)
└── database/
    └── expenses.db      # Created automatically on first run
```

## Testing it without real receipts
You don't need real receipts — write a few lines of text on paper and photograph
it (e.g. "DMART STORES, TOTAL: 450, DATE: 18/06/2026"), or photograph a printed
bill. As long as Tesseract can read text from the image, the pipeline works.

## Report outline (for your written submission)
1. **Abstract** — one paragraph: what problem, what AI, what result.
2. **Introduction** — manual expense tracking is tedious and error-prone.
3. **Literature Survey** — compare regex-based parsing vs. LLM-based parsing
   (mention this is why you chose an LLM — it handles messy/unstructured OCR text
   that fixed rules would fail on).
4. **Problem Statement** — extract structured financial data from unstructured
   receipt photos automatically.
5. **Objectives** — accurate OCR extraction, automatic categorization, queryable
   storage, actionable budget feedback.
6. **System Architecture** — draw the pipeline diagram above.
7. **Implementation** — walk through `app.py` section by section.
8. **Results** — show a few example receipts → extracted JSON → dashboard screenshot.
9. **Conclusion** — summarize what was achieved and that it works end-to-end.
10. **Future Scope** — bank statement import, multi-currency support, monthly PDF reports.

## Likely viva questions
- **Q: Why use an LLM instead of regex to parse the receipt text?**
  A: OCR output is messy and inconsistent (misspelled vendor names, broken line
  breaks, varying receipt formats). Regex rules break easily across formats; an
  LLM understands context and extracts the right fields even from messy text.

- **Q: What happens if there's no internet connection?**
  A: OCR (Tesseract) runs fully offline. Only the structuring step and the new
  AI features (budget tips, NL queries) need Gemini's API, so the app degrades
  gracefully — it falls back to defaults rather than crashing.

- **Q: How does the natural-language query feature actually work?**
  A: The question is sent to Gemini with the database schema. Gemini writes a
  SQL query, which is executed against SQLite, and the resulting rows are sent
  back to Gemini once more to phrase as a plain-English sentence.

- **Q: Why SQLite instead of a CSV or Excel file?**
  A: SQLite supports proper queries (SUM, GROUP BY, filtering by date), which
  is exactly what the dashboard and NL-query feature both depend on, and it
  avoids quirks like Excel reformatting saved dates.
