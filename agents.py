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
from groq import Groq


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
        """Rule-based flags - transparent, no ML black box.

        Uses keyword matching against category names rather than exact
        matches, because the category set differs by customer segment
        (Individual vs SSE/MSE/LSE business current accounts) - e.g. an
        Individual has "Home Loan EMI" while an LSE has "Corporate Loan
        EMI"/"Working Capital Loan EMI". Exact-name matching would silently
        never fire for most segments.
        """
        breakdown = self.category_breakdown(last_n_months=1)
        all_categories_ever = set(self.df["Category"].unique())
        flags = []

        income_this_month = self.df[
            (self.df["Month"] == self.df["Month"].max()) & (self.df["Type"] == "Credit")
        ]["Amount"].sum()

        # EMI-to-income check - mirrors the ~40% EMI/NMI guardrail banks use
        # when assessing a customer's debt burden. Sums ANY category
        # containing "EMI" so it works across every segment's naming.
        emi_this_month = sum(amt for cat, amt in breakdown.items() if "EMI" in cat)
        if income_this_month > 0 and emi_this_month / income_this_month > 0.40:
            pct = emi_this_month / income_this_month * 100
            flags.append(f"Loan EMI is {pct:.0f}% of this month's income - above the typical 40% comfort threshold.")

        # No voluntary savings this month - only meaningful for segments
        # whose history actually includes FD/RD contributions (Individual).
        has_fd_rd_history = bool({"FD Contribution", "RD Contribution"} & all_categories_ever)
        if has_fd_rd_history and breakdown.get("FD Contribution", 0) == 0 and breakdown.get("RD Contribution", 0) == 0:
            flags.append("No voluntary FD/RD contribution recorded this month.")

        # High credit card bill relative to income (Individual).
        cc_bill = breakdown.get("Credit Card Bill Payment", 0)
        if income_this_month > 0 and cc_bill / income_this_month > 0.25:
            flags.append(f"Credit card bill this month (₹{cc_bill:,.0f}) is a large share of income - worth reviewing card usage.")

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


GEMINI_MODEL_DEFAULT = "gemini-3.5-flash"
GROQ_MODEL_DEFAULT = "llama-3.3-70b-versatile"


class WealthStrategist:
    """
    Wraps either Gemini (Google AI Studio) or Groq as the underlying LLM.
    Both are free-tier, no-credit-card providers - having two means a demo
    doesn't go down if one account's daily/per-minute quota is hit, which is
    exactly the problem that motivated adding this. The two providers are
    interchangeable from the caller's side: same recommend() signature,
    same JSON return shape, same fallback behavior on failure.

    Gemini uses a native response_schema (strict JSON schema enforcement).
    Groq's JSON mode only guarantees valid JSON, not a specific shape, so
    the exact required keys are spelled out in the prompt text instead.
    """

    def __init__(self, api_key: str, provider: str = "gemini", model_name: str = None):
        self.provider = provider.lower().strip()
        if self.provider == "gemini":
            genai.configure(api_key=api_key)
            self.model_name = model_name or GEMINI_MODEL_DEFAULT
            self.model = genai.GenerativeModel(
                self.model_name,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": RESPONSE_SCHEMA,
                },
            )
        elif self.provider == "groq":
            self.client = Groq(api_key=api_key)
            self.model_name = model_name or GROQ_MODEL_DEFAULT
        else:
            raise ValueError(f"Unknown provider '{provider}' - expected 'gemini' or 'groq'.")

    def _build_prompt(self, avg_surplus, breakdown_1mo, breakdown_6mo, six_month_totals,
                       flags, user_question, kb_collection):
        breakdown_1mo_text = "\n".join([f"- {cat}: ₹{amt:,.0f}" for cat, amt in breakdown_1mo.items()])
        breakdown_6mo_text = "\n".join([f"- {cat}: ₹{amt:,.0f}" for cat, amt in breakdown_6mo.items()])
        flags_text = "\n".join([f"- {f}" for f in flags]) if flags else "- None"

        # Retrieve only the instrument docs relevant to this query/context
        # instead of always injecting the entire static list. Only works
        # with the Gemini-embedding-backed knowledge base, so Groq sessions
        # always use the static fallback list below - by design, not a bug.
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

        return f"""
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

    def recommend(self, avg_surplus: float, breakdown_1mo: pd.Series, breakdown_6mo: pd.Series,
                  six_month_totals: dict, flags: list[str], user_question: str = None,
                  kb_collection=None) -> dict:
        prompt = self._build_prompt(avg_surplus, breakdown_1mo, breakdown_6mo,
                                     six_month_totals, flags, user_question, kb_collection)

        if self.provider == "gemini":
            response = self.model.generate_content(prompt)
            raw_text = getattr(response, "text", None)
        else:  # groq
            groq_prompt = prompt + (
                "\n\nReturn a single JSON object with EXACTLY these keys: "
                '"summary" (string), "reasoning" (string), "allocations" '
                '(array of objects, each with "instrument" (string), "amount" '
                '(number), "risk_level" ("Low" or "Medium"), "why" (string)). '
                "No other keys, no markdown formatting, no code fences."
            )
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": groq_prompt}],
                response_format={"type": "json_object"},
                temperature=0.4,
            )
            raw_text = completion.choices[0].message.content

        try:
            return json.loads(raw_text)
        except (json.JSONDecodeError, TypeError):
            return {
                "summary": "I had trouble structuring a full recommendation just now.",
                "reasoning": raw_text if raw_text else "No response text available.",
                "allocations": [],
            }