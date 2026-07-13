# Digital Wealth Assistant — Prototype
Hackathon: IDBI Innovate 2026 — Problem Statement 1 (Digital Wealth Management, Avatar-based)

Independent prototype. Not affiliated with or built using any real IDBI Bank
code, data, or branding. All accounts, users, and transactions are synthetic.

## What this is
- **Login screen**: 10 synthetic demo users, each with a distinct income/
  spending profile. Password for every demo account: `Idbi@123` (shown on
  the login screen itself for judges).
- **Agent A — Budget Analyst**: pure pandas logic (no LLM) that parses the
  logged-in user's transaction history and computes monthly surplus,
  category spend, and simple rule-based behavioral flags. Deterministic and
  auditable by design.
- **Agent B — Wealth Strategist**: calls the free Gemini API with a
  constrained prompt (fixed instrument list, surplus cap) and asks for
  **structured JSON**, which the UI renders as clean recommendation cards
  instead of a text blob.
- **Quick-reply buttons**: common questions (this month's recommendation,
  "am I overspending?", "how can I save more?", "explain FD vs RD vs PPF")
  next to the free-text chat box.
- **Disclaimer** appears once, in the panel footer — not repeated by the AI.

## 1. Run it locally
```bash
cd wealth_prototype
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python generate_data.py         # creates mock_transactions.csv + mock_users.csv
streamlit run app.py
```
Opens at `http://localhost:8501`. Log in with any demo username (e.g.
`priya.s`) and password `Idbi@123`, then paste your free Gemini API key
(https://aistudio.google.com/apikey) into the sidebar.

**Security note:** the API key field is masked (password-style) by design.
If you ever see the key rendered in plain text anywhere - a screenshot, a
terminal log, a shared screen - treat it as compromised and generate a new
one immediately from the AI Studio dashboard. Never paste it into chat with
anyone, including an AI assistant.

## 2. Deploy it live
1. Push this folder to a new **public GitHub repo**. Do NOT commit an API
   key anywhere in the code - the app only ever takes it via the sidebar
   at runtime.
2. Go to https://share.streamlit.io → "New app" → sign in with GitHub.
3. Point it at your repo, main file `app.py`.
4. Deploy → you get a public URL like `https://your-app-name.streamlit.app`.

## 3. Files
- `app.py` — main Streamlit app: login, dashboard, avatar/chat panel
- `agents.py` — Agent A (Budget Analyst) and Agent B (Wealth Strategist)
- `generate_data.py` — generates 10 synthetic users x ~500 transactions each
  over 6 months (run once, or to regenerate)
- `mock_transactions.csv` — generated synthetic transaction data
- `mock_users.csv` — generated demo login credentials (hashed passwords)
- `requirements.txt` — dependencies

## 4. Compliance notes 
- No real customer data or PII anywhere — all users and transactions are
  fabricated by `generate_data.py`.
- Passwords are stored as SHA-256 hashes, not plaintext, even for this
  synthetic demo data (mirrors real banking hygiene practice).
- User IDs are tokenized (`USER_xxxx`) rather than real names/account numbers.
- Agent A's reasoning is plain arithmetic on visible columns — fully
  auditable, not a black box.
- Agent B is constrained to a fixed, pre-approved instrument list and a
  hard cap on equity exposure (max 20%), and the mandatory "not SEBI/RBI
  registered investment advice" disclaimer is shown once, consistently, by
  the app itself rather than relying on the LLM to include it.
- This structure mirrors an RBI-style regulatory sandbox: real bank
  integration and real datasets would only happen after this design is
  reviewed, with the bank's actual sandbox APIs replacing the synthetic
  CSV — nothing here talks to a live banking system.

## 5. Ideas to extend if you have more time
- Swap the pie/line charts for a "goal tracker" (e.g., progress toward a
  PPF/FD goal).
- Add text-to-speech (gTTS, free) so the avatar "speaks" its recommendation.
- Move the safe-instrument list into a small local knowledge base file to
  make it easy to demo "RAG" in your architecture slide.
- Add session-timeout / auto-logout to mirror real net-banking security
  behavior (IDBI's actual portal does this).

