"""
Generates synthetic multi-user banking data for the prototype, modeled on
IDBI Bank's actual customer segments and transaction types:

- Individual (Retail): loan + FD/RD-centric bank activity - EMIs, deposit
  contributions, insurance premiums. No discretionary lifestyle spend
  categories (no Groceries/Dining/Entertainment/Education/Shopping) - this
  is deliberately scoped to the loan-and-deposit relationship IDBI has with
  a retail customer, not a full consumer spend simulation.
- Small-Scale Enterprise (SSE), Medium-Scale Enterprise (MSE),
  Large-Scale Enterprise (LSE): Current Account holders with
  business-realistic transaction types - vendor payments, payroll,
  GST, equipment/facility leases, machinery & asset purchases (capex),
  working capital/corporate loan EMIs, and - for MSE/LSE - trade finance
  charges (LC/BG) and foreign currency import/export, reflecting IDBI's
  trade finance and digital/electronic (RTGS/NEFT) transaction types.
  LSE additionally gets a rare one-off project financing disbursement and
  debt syndication fee, reflecting IDBI's investment & advisory business.

No real customer or company data anywhere - purely fabricated for demo
purposes. Company names are fictional.

Run once: python generate_data.py
Outputs: mock_transactions.csv, mock_users.csv
"""
import pandas as pd
import numpy as np
import hashlib
from datetime import datetime, timedelta
import random

random.seed(11)
np.random.seed(11)

START_DATE = datetime(2026, 1, 1)
NUM_MONTHS = 6
DEFAULT_PASSWORD = "Idbi@123"


def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


def days_in_month(month_start: datetime) -> int:
    nxt = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return (nxt - month_start).days


def next_month(month_start: datetime) -> datetime:
    return (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)


def payment_mode_for(category: str, amount: float, segment: str) -> str:
    """Mirrors real settlement rails: standing-instruction items go via
    Auto-Debit (NACH); everyday consumer bill-pay can be UPI; everything
    else scales by ticket size - RTGS for high-value, NEFT for mid-value,
    Net Banking for smaller/manual transfers."""
    if category in ("Loan EMI", "Insurance Premium", "Home Loan EMI",
                     "Personal Loan EMI", "Auto Loan EMI", "Working Capital Loan EMI",
                     "Corporate Loan EMI", "Business Insurance Premium"):
        return "Auto-Debit (NACH)"
    if segment == "Individual":
        if category == "Utility Bill Payment":
            return random.choice(["UPI", "Net Banking"])
        return "Net Banking"
    if amount >= 2_000_000:
        return "RTGS"
    if amount >= 200_000:
        return np.random.choice(["RTGS", "NEFT"], p=[0.4, 0.6])
    return np.random.choice(["NEFT", "Net Banking"], p=[0.6, 0.4])


# ---------------------------------------------------------------------------
# INDIVIDUAL (Retail) personas - loan & deposit relationship only
# ---------------------------------------------------------------------------
INDIVIDUAL_PERSONAS = [
    {"username": "aarav.k", "name": "Aarav Kumar", "salary": 85000,
     "loan_type": "Home Loan EMI", "emi": 32000, "fd_monthly": 6000,
     "rd_monthly": 3000, "insurance": 2500},
    {"username": "priya.s", "name": "Priya Sharma", "salary": 95000,
     "loan_type": "Personal Loan EMI", "emi": 18000, "fd_monthly": 10000,
     "rd_monthly": 4000, "insurance": 3000},
    {"username": "rohan.m", "name": "Rohan Mehta", "salary": 70000,
     "loan_type": "Auto Loan EMI", "emi": 15000, "fd_monthly": 5000,
     "rd_monthly": 2500, "insurance": 2000},
]

# ---------------------------------------------------------------------------
# ENTERPRISE (Current Account) personas - Small / Medium / Large scale
# ---------------------------------------------------------------------------
ENTERPRISE_PERSONAS = [
    {"username": "sneha.textiles", "name": "Sneha Textiles Pvt Ltd",
     "segment": "Small-Scale Enterprise", "monthly_revenue": 900_000,
     "vendor_pct": 0.35, "payroll_pct": 0.20, "gst_pct": 0.06,
     "lease": 40_000, "loan_emi": 25_000, "insurance": 8_000,
     "capex_chance": 0.15, "capex_range": (80_000, 250_000)},
    {"username": "karan.autoparts", "name": "Karan Auto Components",
     "segment": "Small-Scale Enterprise", "monthly_revenue": 700_000,
     "vendor_pct": 0.38, "payroll_pct": 0.18, "gst_pct": 0.06,
     "lease": 30_000, "loan_emi": 20_000, "insurance": 6_000,
     "capex_chance": 0.12, "capex_range": (60_000, 200_000)},
    {"username": "diya.foods", "name": "Diya Foods & Beverages",
     "segment": "Small-Scale Enterprise", "monthly_revenue": 1_100_000,
     "vendor_pct": 0.40, "payroll_pct": 0.16, "gst_pct": 0.06,
     "lease": 45_000, "loan_emi": 28_000, "insurance": 9_000,
     "capex_chance": 0.15, "capex_range": (100_000, 300_000)},
    {"username": "arjun.engineering", "name": "Arjun Engineering Works",
     "segment": "Medium-Scale Enterprise", "monthly_revenue": 6_500_000,
     "vendor_pct": 0.40, "payroll_pct": 0.18, "gst_pct": 0.07,
     "lease": 250_000, "loan_emi": 180_000, "insurance": 45_000,
     "capex_chance": 0.25, "capex_range": (500_000, 2_000_000),
     "trade_finance_chance": 0.3, "trade_finance_range": (15_000, 60_000),
     "import_chance": 0.2, "import_range": (300_000, 1_200_000)},
    {"username": "meera.pharma", "name": "Meera Pharma Manufacturing",
     "segment": "Medium-Scale Enterprise", "monthly_revenue": 9_000_000,
     "vendor_pct": 0.42, "payroll_pct": 0.16, "gst_pct": 0.07,
     "lease": 320_000, "loan_emi": 240_000, "insurance": 60_000,
     "capex_chance": 0.25, "capex_range": (700_000, 2_500_000),
     "trade_finance_chance": 0.3, "trade_finance_range": (20_000, 80_000),
     "import_chance": 0.25, "import_range": (400_000, 1_500_000)},
    {"username": "vikram.steel", "name": "Vikram Steel Industries",
     "segment": "Large-Scale Enterprise", "monthly_revenue": 45_000_000,
     "vendor_pct": 0.42, "payroll_pct": 0.15, "gst_pct": 0.08,
     "lease": 1_200_000, "loan_emi": 2_500_000, "insurance": 300_000,
     "capex_chance": 0.4, "capex_range": (8_000_000, 30_000_000),
     "trade_finance_chance": 0.5, "trade_finance_range": (100_000, 400_000),
     "import_chance": 0.35, "import_range": (3_000_000, 15_000_000),
     "export_chance": 0.3, "export_range": (2_000_000, 12_000_000),
     "project_finance_chance": 0.15, "project_finance_range": (50_000_000, 200_000_000),
     "syndication_fee_chance": 0.1, "syndication_fee_range": (500_000, 2_000_000)},
    {"username": "ananya.energy", "name": "Ananya Power & Energy Ltd",
     "segment": "Large-Scale Enterprise", "monthly_revenue": 60_000_000,
     "vendor_pct": 0.40, "payroll_pct": 0.13, "gst_pct": 0.08,
     "lease": 1_500_000, "loan_emi": 3_200_000, "insurance": 380_000,
     "capex_chance": 0.4, "capex_range": (10_000_000, 40_000_000),
     "trade_finance_chance": 0.5, "trade_finance_range": (150_000, 500_000),
     "import_chance": 0.35, "import_range": (4_000_000, 18_000_000),
     "export_chance": 0.3, "export_range": (3_000_000, 15_000_000),
     "project_finance_chance": 0.15, "project_finance_range": (70_000_000, 250_000_000),
     "syndication_fee_chance": 0.1, "syndication_fee_range": (700_000, 2_500_000)},
]

txn_rows = []
user_rows = []
ID_PREFIX = {"Individual": "IND", "Small-Scale Enterprise": "SSE",
             "Medium-Scale Enterprise": "MSE", "Large-Scale Enterprise": "LSE"}
txn_id_counter = [1]


def add_txn(user_id, date, category, amount, ttype, balance, segment):
    txn_rows.append([txn_id_counter[0], user_id, date.strftime("%Y-%m-%d"), category,
                      round(amount, 2), ttype, round(balance, 2),
                      payment_mode_for(category, amount, segment)])
    txn_id_counter[0] += 1


# --- Individuals ---
for persona in INDIVIDUAL_PERSONAS:
    segment = "Individual"
    user_id = f"{ID_PREFIX[segment]}_{random.randint(1000,9999)}"
    balance = round(random.uniform(150_000, 400_000), 2)
    month_start = START_DATE

    for m in range(NUM_MONTHS):
        n_days = days_in_month(month_start)

        balance += persona["salary"]
        add_txn(user_id, month_start, "Salary", persona["salary"], "Credit", balance, segment)

        emi_date = month_start + timedelta(days=4)
        balance -= persona["emi"]
        add_txn(user_id, emi_date, persona["loan_type"], persona["emi"], "Debit", balance, segment)

        fd_date = month_start + timedelta(days=6)
        balance -= persona["fd_monthly"]
        add_txn(user_id, fd_date, "FD Contribution", persona["fd_monthly"], "Debit", balance, segment)

        rd_date = month_start + timedelta(days=7)
        balance -= persona["rd_monthly"]
        add_txn(user_id, rd_date, "RD Contribution", persona["rd_monthly"], "Debit", balance, segment)

        ins_date = month_start + timedelta(days=9)
        balance -= persona["insurance"]
        add_txn(user_id, ins_date, "Insurance Premium", persona["insurance"], "Debit", balance, segment)

        if random.random() < 0.85:
            amt = round(random.uniform(3000, 12000), 2)
            date = month_start + timedelta(days=random.randint(10, 15))
            balance -= amt
            add_txn(user_id, date, "Credit Card Bill Payment", amt, "Debit", balance, segment)

        for _ in range(random.randint(1, 2)):
            amt = round(random.uniform(800, 3500), 2)
            date = month_start + timedelta(days=random.randint(0, n_days - 1))
            balance -= amt
            add_txn(user_id, date, "Utility Bill Payment", amt, "Debit", balance, segment)

        if m % 3 == 2:
            amt = round(random.uniform(1500, 6000), 2)
            date = month_start + timedelta(days=n_days - 2)
            balance += amt
            add_txn(user_id, date, "Interest Credited", amt, "Credit", balance, segment)

        month_start = next_month(month_start)

    user_rows.append({"username": persona["username"], "password_hash": hash_password(DEFAULT_PASSWORD),
                       "display_name": persona["name"], "user_id": user_id, "segment": segment})

# --- Enterprises ---
for persona in ENTERPRISE_PERSONAS:
    segment = persona["segment"]
    user_id = f"{ID_PREFIX[segment]}_{random.randint(1000,9999)}"
    mult = 8 if segment == "Large-Scale Enterprise" else 3 if segment == "Medium-Scale Enterprise" else 1
    balance = round(random.uniform(500_000, 2_000_000) * mult, 2)
    month_start = START_DATE

    for m in range(NUM_MONTHS):
        n_days = days_in_month(month_start)
        revenue = persona["monthly_revenue"] * random.uniform(0.85, 1.15)

        n_receipts = random.randint(8, 14)
        for w in np.random.dirichlet(np.ones(n_receipts) * 3):
            amt = round(max(w * revenue, 5000), 2)
            date = month_start + timedelta(days=random.randint(0, n_days - 1))
            balance += amt
            add_txn(user_id, date, "Customer Receipt / Sales Revenue", amt, "Credit", balance, segment)

        vendor_total = revenue * persona["vendor_pct"]
        n_vendor = random.randint(8, 14)
        for w in np.random.dirichlet(np.ones(n_vendor) * 3):
            amt = round(max(w * vendor_total, 3000), 2)
            date = month_start + timedelta(days=random.randint(0, n_days - 1))
            balance -= amt
            add_txn(user_id, date, "Vendor Payment", amt, "Debit", balance, segment)

        payroll = revenue * persona["payroll_pct"]
        date = month_start + timedelta(days=min(n_days - 1, 27))
        balance -= payroll
        add_txn(user_id, date, "Payroll Disbursement", payroll, "Debit", balance, segment)

        gst = revenue * persona["gst_pct"]
        date = month_start + timedelta(days=min(n_days - 1, 19))
        balance -= gst
        add_txn(user_id, date, "GST Payment", gst, "Debit", balance, segment)

        date = month_start + timedelta(days=4)
        balance -= persona["lease"]
        add_txn(user_id, date, "Equipment/Facility Lease Payment", persona["lease"], "Debit", balance, segment)

        emi_label = "Working Capital Loan EMI" if segment == "Small-Scale Enterprise" else "Corporate Loan EMI"
        date = month_start + timedelta(days=6)
        balance -= persona["loan_emi"]
        add_txn(user_id, date, emi_label, persona["loan_emi"], "Debit", balance, segment)

        date = month_start + timedelta(days=9)
        balance -= persona["insurance"]
        add_txn(user_id, date, "Business Insurance Premium", persona["insurance"], "Debit", balance, segment)

        if random.random() < persona["capex_chance"]:
            lo, hi = persona["capex_range"]
            amt = round(random.uniform(lo, hi), 2)
            date = month_start + timedelta(days=random.randint(0, n_days - 1))
            balance -= amt
            add_txn(user_id, date, "Machinery/Asset Purchase", amt, "Debit", balance, segment)

        if persona.get("trade_finance_chance", 0) and random.random() < persona["trade_finance_chance"]:
            lo, hi = persona["trade_finance_range"]
            amt = round(random.uniform(lo, hi), 2)
            date = month_start + timedelta(days=random.randint(0, n_days - 1))
            balance -= amt
            add_txn(user_id, date, "Trade Finance Charges (LC/BG)", amt, "Debit", balance, segment)

        if persona.get("import_chance", 0) and random.random() < persona["import_chance"]:
            lo, hi = persona["import_range"]
            amt = round(random.uniform(lo, hi), 2)
            date = month_start + timedelta(days=random.randint(0, n_days - 1))
            balance -= amt
            add_txn(user_id, date, "Import Payment (Foreign Currency)", amt, "Debit", balance, segment)

        if persona.get("export_chance", 0) and random.random() < persona["export_chance"]:
            lo, hi = persona["export_range"]
            amt = round(random.uniform(lo, hi), 2)
            date = month_start + timedelta(days=random.randint(0, n_days - 1))
            balance += amt
            add_txn(user_id, date, "Export Receipt (Foreign Currency)", amt, "Credit", balance, segment)

        if persona.get("project_finance_chance", 0) and random.random() < persona["project_finance_chance"]:
            lo, hi = persona["project_finance_range"]
            amt = round(random.uniform(lo, hi), 2)
            date = month_start + timedelta(days=random.randint(0, n_days - 1))
            balance += amt
            add_txn(user_id, date, "Project Financing Disbursement", amt, "Credit", balance, segment)

        if persona.get("syndication_fee_chance", 0) and random.random() < persona["syndication_fee_chance"]:
            lo, hi = persona["syndication_fee_range"]
            amt = round(random.uniform(lo, hi), 2)
            date = month_start + timedelta(days=random.randint(0, n_days - 1))
            balance -= amt
            add_txn(user_id, date, "Debt Syndication Fee", amt, "Debit", balance, segment)

        month_start = next_month(month_start)

    user_rows.append({"username": persona["username"], "password_hash": hash_password(DEFAULT_PASSWORD),
                       "display_name": persona["name"], "user_id": user_id, "segment": segment})

txn_df = pd.DataFrame(txn_rows, columns=["Transaction_ID", "User_ID", "Timestamp", "Category",
                                          "Amount", "Type", "Balance_After", "Payment_Mode"])
txn_df = txn_df.sort_values(["User_ID", "Timestamp"]).reset_index(drop=True)
users_df = pd.DataFrame(user_rows)

txn_df.to_csv("mock_transactions.csv", index=False)
users_df.to_csv("mock_users.csv", index=False)

print(f"Generated {len(txn_df)} transactions across {len(users_df)} users "
      f"({len(txn_df)/len(users_df):.0f} avg/user).")
print(f"Segments: {users_df['segment'].value_counts().to_dict()}")
print(f"Demo login for all users -> password: {DEFAULT_PASSWORD}\n")

for uid in txn_df["User_ID"].unique():
    sub = txn_df[txn_df["User_ID"] == uid].sort_values("Timestamp")
    print(f"{uid}: ending balance Rs.{sub.iloc[-1]['Balance_After']:,.0f}")
