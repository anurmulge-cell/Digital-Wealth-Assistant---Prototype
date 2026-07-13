"""
agents.py
Contains the two AI agents for the Digital Wealth Management prototype:

Agent A - Budget Analyst: pure data analysis (pandas). Deterministic, auditable,
          no black-box behavior - this is intentional for explainability.
Agent B - Wealth Strategist: takes Agent A's numbers and calls an LLM (Gemini)
          with a constrained, rules-based prompt to produce a personalized,
          explainable, low/medium-risk investment recommendation as
          structured JSON (so the UI can render it as clean cards, not a
          wall of text).
"""

import json
import pandas as pd
import google.generativeai as genai


# ---------------------------------------------------------------------------
# Agent A: Budget Analyst
# ---------------------------------------------------------------------------
class BudgetAnalyst:
    """Parses one user's transaction history and computes spending behavior metrics."""

    def __init__(self, df: pd.DataFrame, user_id: str):
        self.df = df[df["User_ID"] == user_id].copy()
        self.df["Timestamp"] = pd.to_datetime(self.df["Timestamp"])
        self.df["Month"] = self.df["Timestamp"].dt.to_period("M")

    def monthly_summary(self):
        credit = self.df[self.df["Type"] == "Credit"].groupby("Month")["Amount"].sum()
        debit = self.df[self.df["Type"] == "Debit"].groupby("Month")["Amount"].sum()
        summary = pd.DataFrame({"Income": credit, "Spend": debit}).fillna(0)
        summary["Surplus"] = summary["Income"] - summary["Spend"]
        return summary

    def category_breakdown(self, last_n_months: int = 1):
        recent_months = sorted(self.df["Month"].unique())[-last_n_months:]
        subset = self.df[(self.df["Month"].isin(recent_months)) & (self.df["Type"] == "Debit")]
        return subset.groupby("Category")["Amount"].sum().sort_values(ascending=False)

    def latest_balance(self):
        return self.df.sort_values("Timestamp").iloc[-1]["Balance_After"]

    def average_surplus(self):
        summary = self.monthly_summary()
        if len(summary) > 2:
            summary = summary.iloc[1:-1]
        return round(summary["Surplus"].mean(), 2)

    def flags(self):
        """Simple rule-based flags - transparent, no ML black box."""
        breakdown = self.category_breakdown(last_n_months=1)
        flags = []
        if breakdown.get("Dining", 0) > 5000:
            flags.append("High dining spend this month (>₹5,000).")
        if breakdown.get("Entertainment", 0) > 4000:
            flags.append("Entertainment spend is elevated this month.")
        if breakdown.get("Investment", 0) == 0:
            flags.append("No voluntary investment activity recorded this month.")
        # EMI-to-income check - mirrors the ~40-50% EMI/NMI guardrail banks
        # use when assessing a customer's debt burden.
        income_this_month = self.df[
            (self.df["Month"] == self.df["Month"].max()) & (self.df["Type"] == "Credit")
        ]["Amount"].sum()
        emi_this_month = breakdown.get("Loan EMI", 0)
        if income_this_month > 0 and emi_this_month / income_this_month > 0.40:
            pct = emi_this_month / income_this_month * 100
            flags.append(f"Loan EMI is {pct:.0f}% of this month's income - above the typical 40% comfort threshold.")
        return flags

    def payment_mode_breakdown(self, last_n_months: int = 1):
        """Debit spend grouped by payment mode (UPI / Debit Card / Credit Card / Net Banking)."""
        recent_months = sorted(self.df["Month"].unique())[-last_n_months:]
        subset = self.df[(self.df["Month"].isin(recent_months)) & (self.df["Type"] == "Debit")]
        return subset.groupby("Payment_Mode")["Amount"].sum().sort_values(ascending=False)

    def recent_transactions(self, n: int = 8):
        """Most recent n transactions with payment mode, for a card/UPI activity feed."""
        cols = ["Timestamp", "Category", "Amount", "Type", "Payment_Mode"]
        return self.df.sort_values("Timestamp", ascending=False)[cols].head(n)

    def six_month_totals(self):
        """Total income/spend/surplus across all available months (up to 6)."""
        summary = self.monthly_summary()
        return {
            "total_income": round(summary["Income"].sum(), 2),
            "total_spend": round(summary["Spend"].sum(), 2),
            "total_surplus": round(summary["Surplus"].sum(), 2),
            "num_months": len(summary),
        }


# ---------------------------------------------------------------------------
# Agent B: Wealth Strategist
# ---------------------------------------------------------------------------
SAFE_INSTRUMENTS_CONTEXT = """
You may only recommend from this fixed set of low-to-medium risk instruments
(this list simulates the bank's approved/RBI-compliant product shelf):
- Recurring Deposit (RD): guaranteed returns, ~6-7% p.a., good for building a habit with small monthly surplus.
- Fixed Deposit (FD): guaranteed returns, ~6.5-7.5% p.a., good for lump-sum surplus, low liquidity need.
- Public Provident Fund (PPF): government-backed, ~7-8% p.a., long lock-in (15 yrs), tax benefits under 80C.
- Debt Mutual Funds: low-medium risk, ~7-9% p.a. historically, more liquid than FD.
- Large-cap Equity Mutual Funds (SIP only, max 20% of surplus): medium risk, only if surplus is consistently positive
  for 3+ months, always frame as long-term (5+ years).
"""

# Single source of truth for the disclaimer - rendered ONCE by the UI footer.
# The LLM is explicitly told NOT to repeat it, to avoid duplication.
DISCLAIMER = (
    "This is an AI-generated educational insight based on your transaction patterns. "
    "It does not constitute SEBI/RBI registered investment advice. Please consult a "
    "certified financial advisor before making investment decisions."
)

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "description": "1-2 sentence plain-language summary of the recommendation."},
        "reasoning": {"type": "string", "description": "Plain-terms explanation referencing the user's actual numbers."},
        "allocations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "instrument": {"type": "string"},
                    "amount": {"type": "number"},
                    "risk_level": {"type": "string", "enum": ["Low", "Medium"]},
                    "why": {"type": "string", "description": "One short sentence on why this instrument, for this user."},
                },
                "required": ["instrument", "amount", "risk_level", "why"],
            },
        },
    },
    "required": ["summary", "reasoning", "allocations"],
}


class WealthStrategist:
    def __init__(self, api_key: str, model_name: str = "gemini-3.5-flash"):
        genai.configure(api_key=api_key)
        self.model_name = model_name
        self.model = genai.GenerativeModel(
            model_name,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": RESPONSE_SCHEMA,
            },
        )

    def recommend(self, avg_surplus: float, breakdown_1mo: pd.Series, breakdown_6mo: pd.Series,
                  six_month_totals: dict, flags: list[str], user_question: str = None,
                  kb_collection=None) -> dict:
        breakdown_1mo_text = "\n".join([f"- {cat}: ₹{amt:,.0f}" for cat, amt in breakdown_1mo.items()])
        breakdown_6mo_text = "\n".join([f"- {cat}: ₹{amt:,.0f}" for cat, amt in breakdown_6mo.items()])
        flags_text = "\n".join([f"- {f}" for f in flags]) if flags else "- None"

        # Retrieve only the instrument docs relevant to this query/context
        # instead of always injecting the entire static list. Falls back to
        # the full static list if the vector DB isn't available (no key yet,
        # network hiccup, etc.) so the app never breaks because of this.
        instruments_context = SAFE_INSTRUMENTS_CONTEXT
        if kb_collection is not None:
            try:
                from knowledge_base import retrieve_relevant_instruments
                query = user_question or f"recommendation for surplus of Rs.{avg_surplus:,.0f}"
                retrieved = retrieve_relevant_instruments(kb_collection, query, k=3)
                if retrieved:
                    instruments_context = (
                        "You may only recommend from these instruments retrieved as most "
                        "relevant to this user (approved/RBI-compliant product shelf):\n"
                        + "\n".join(f"- {doc}" for doc in retrieved)
                    )
            except Exception:
                pass  # keep static fallback above

        prompt = f"""
You are "WealthAssist", an AI wealth advisory assistant embedded inside a bank's
mobile/net-banking app prototype. You must be conservative, transparent, and
compliant with RBI/SEBI guardrails.

Rules you MUST follow:
1. If the user asked a specific question, answer THAT question directly and
   precisely first, using the exact time period they asked about (this month
   vs. last 6 months) - do not default to only this month's numbers if they
   asked about a longer period.
2. Only populate "allocations" if the user asked for a recommendation/investment
   suggestion, or if no question was given (default task). If they asked a
   factual question (e.g. "what did I spend"), leave allocations empty and put
   the direct answer in "summary".
3. When you do recommend, only use instruments from the approved list below,
   reference the user's actual numbers, and keep total allocated amount to a
   MAXIMUM of the user's average monthly surplus. If surplus is zero or
   negative, explain that in "summary" instead of allocating anything.
4. Never claim guaranteed high returns. Never allocate more than 20% of surplus to equity.
5. Do NOT include any disclaimer text yourself - the app displays it separately.
6. Keep language simple, warm, non-jargon, and specific (cite real numbers, not vague terms).

{instruments_context}

User's financial snapshot (synthetic/masked data, no real PII):
- Average monthly surplus (recent months): ₹{avg_surplus:,.0f}
- This month's spend by category:
{breakdown_1mo_text}
- Last {six_month_totals['num_months']} months combined: income ₹{six_month_totals['total_income']:,.0f},
  spend ₹{six_month_totals['total_spend']:,.0f}, net surplus ₹{six_month_totals['total_surplus']:,.0f}
- Last {six_month_totals['num_months']} months spend by category (all months combined):
{breakdown_6mo_text}
- Behavioral flags detected by the Budget Analyst agent:
{flags_text}

{"User's question: " + user_question if user_question else "Task: Give this user a personalized wealth recommendation for this month's surplus."}

Respond ONLY with JSON matching the required schema.
"""
        response = self.model.generate_content(prompt)
        try:
            return json.loads(response.text)
        except (json.JSONDecodeError, AttributeError):
            return {
                "summary": "I had trouble structuring a full recommendation just now.",
                "reasoning": response.text if hasattr(response, "text") else "No response text available.",
                "allocations": [],
            }