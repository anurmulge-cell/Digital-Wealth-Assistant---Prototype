"""
app.py - Digital Wealth Management Prototype (Avatar-based AI Advisor)
Built for IDBI Innovate 2026 - Problem Statement 1

IMPORTANT: This is an independent hackathon prototype. It is NOT affiliated
with, endorsed by, or built using any real IDBI Bank code, data, or branding.
All account names, balances, transactions, and login credentials are
synthetic/fabricated for demonstration only.
"""

import hashlib
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from agents import BudgetAnalyst, WealthStrategist, DISCLAIMER
from tts import text_to_speech_bytes
from avatar import get_avatar_html
import knowledge_base as kb

st.set_page_config(page_title="Digital Wealth Assistant - Prototype", page_icon="\U0001F4B0", layout="wide")

st.markdown("""
<style>
    .main { background-color: #F7F9FA; }
    .acct-card {
        background: linear-gradient(135deg, #0B3D2E 0%, #14563F 100%);
        color: white; border-radius: 14px; padding: 20px; margin-bottom: 10px;
    }
    .acct-card h3 { margin: 0; font-size: 14px; opacity: 0.8; font-weight: 400; }
    .acct-card h1 { margin: 4px 0 0 0; font-size: 28px; }
    .avatar-header { display:flex; align-items:center; gap:12px; margin-bottom: 10px; }
    .avatar-circle {
        min-width: 56px; width: 56px; height: 56px; border-radius: 50%;
        background: radial-gradient(circle at 35% 30%, #4FD1A5, #0B3D2E);
        display:flex; align-items:center; justify-content:center; font-size: 26px;
    }
    .avatar-name { font-weight: 700; font-size: 16px; color: #0B3D2E; margin: 0; }
    .avatar-sub { font-size: 12px; color: #8A96A3; margin: 0; }
    .flag-card {
        background:#FFF7ED; border-left: 3px solid #D97706; border-radius: 8px;
        padding: 8px 12px; margin-bottom: 6px; font-size: 13px; color: #92400E;
    }
    .no-flag-card {
        background:#F0FDF4; border-left: 3px solid #16A34A; border-radius: 8px;
        padding: 8px 12px; margin-bottom: 6px; font-size: 13px; color: #166534;
    }
    .rec-card {
        background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px;
        padding: 12px 14px; margin-bottom: 8px;
    }
    .rec-instrument { font-weight: 700; color: #0B3D2E; font-size: 14px; }
    .rec-amount { font-weight: 700; color: #14563F; font-size: 15px; float: right; }
    .risk-pill {
        display:inline-block; font-size: 11px; padding: 2px 8px; border-radius: 10px;
        margin-left: 6px;
    }
    .risk-low { background:#DCFCE7; color:#166534; }
    .risk-medium { background:#FEF3C7; color:#92400E; }
    .rec-why { font-size: 12px; color:#64748B; margin-top: 4px; }
    .disclaimer-box {
        font-size: 12.5px; color: #7C2D12; background: #FFF7ED;
        border: 1px solid #FDBA74; border-left: 4px solid #EA580C;
        border-radius: 8px; padding: 10px 12px; margin-top: 14px;
        line-height: 1.5;
    }
    .disclaimer-box b { color: #7C2D12; }
    .bill-row, .txn-row {
        display:flex; justify-content:space-between; padding: 8px 4px;
        border-bottom: 1px solid #EEF2F5; font-size: 13px;
    }
    div[data-testid="stChatMessageContent"] { font-size: 14px; }
    button[kind="secondary"][aria-pressed="true"] { border-color: #0B3D2E !important; color: #0B3D2E !important; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    txns = pd.read_csv("mock_transactions.csv")
    users = pd.read_csv("mock_users.csv")
    return txns, users

txns_df, users_df = load_data()


def hash_password(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()


def check_login(username: str, password: str):
    row = users_df[users_df["username"] == username]
    if row.empty:
        return None
    if row.iloc[0]["password_hash"] == hash_password(password):
        return row.iloc[0].to_dict()
    return None


# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
for key, default in [
    ("logged_in", False), ("chat_history", []), ("api_key", ""), ("active_page", "Accounts"),
    ("avatar_url", ""), ("avatar_speaking", False), ("kb_collection", None), ("kb_key_used", None),
    ("avatar_slots", {"Avatar 1": "", "Avatar 2": ""}), ("active_avatar", "Avatar 1"),
    ("ai_provider", "Gemini"), ("groq_api_key", ""),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def get_active_api_key_and_provider():
    """Single source of truth for which provider/key is currently selected,
    so the run_strategist() closures never drift out of sync with the sidebar."""
    if st.session_state.ai_provider == "Groq":
        return st.session_state.groq_api_key, "groq"
    return st.session_state.api_key, "gemini"


# ---------------------------------------------------------------------------
# LOGIN SCREEN
# ---------------------------------------------------------------------------
def render_login():
    st.markdown("## \U0001F3E6 Digital Wealth Assistant \u2014 Prototype")
    st.caption("Simulated bank login | Demo build for hackathon evaluation")
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        with st.container(border=True):
            st.markdown("#### Customer Login")
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="e.g. priya.s")
                password = st.text_input("Password", type="password", placeholder="Demo password: Idbi@123")
                submitted = st.form_submit_button("Login", use_container_width=True)
            if submitted:
                user = check_login(username.strip(), password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.current_user = user
                    st.session_state.chat_history = []
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            with st.expander("Demo accounts (for judges/testing)"):
                st.caption("All demo accounts share the same password: **Idbi@123**")
                st.dataframe(users_df[["username", "display_name"]], hide_index=True, use_container_width=True)


# ---------------------------------------------------------------------------
# Nav bar
# ---------------------------------------------------------------------------
PAGES = ["Accounts", "Transfers", "Bill Payments", "Investments"]

def render_nav():
    cols = st.columns(len(PAGES))
    for i, page in enumerate(PAGES):
        is_active = st.session_state.active_page == page
        if cols[i].button(page, key=f"nav_{page}", use_container_width=True,
                           type="primary" if is_active else "secondary"):
            st.session_state.active_page = page
            st.rerun()


# ---------------------------------------------------------------------------
# Contextual quick-prompts per page
# ---------------------------------------------------------------------------
QUICK_PROMPTS = {
    "Accounts": [
        ("\U0001F4A1 This month's recommendation", None),
        ("\U0001F4B5 Am I overspending?", "Am I overspending this month, and in which categories specifically?"),
        ("\U0001F4C8 How can I save more?", "What is one practical change I can make to save more, based on my actual spending?"),
        ("\U0001F4CA Spend: this month vs 6mo", "What is my total spend this month, and what is my total spend over the last 6 months?"),
    ],
    "Transfers": [
        ("\U0001F512 Is a new payee transfer safe?", "What precautions should I take before transferring money to a new payee?"),
        ("\u26A1 IMPS vs NEFT vs RTGS", "Explain the difference between IMPS, NEFT, and RTGS simply, and when to use each."),
    ],
    "Bill Payments": [
        ("\U0001F4C5 Which bills drain my budget?", "Based on my spending categories, which recurring bills or subscriptions are the biggest drain on my budget?"),
        ("\U0001F916 Should I automate bill payments?", "Would automating my bill payments help my financial habits, based on my spending pattern?"),
    ],
    "Investments": [
        ("\U0001F4B0 Recommend investments now", None),
        ("\U0001F3E6 Explain FD vs RD vs PPF", "Explain the difference between FD, RD, and PPF simply, and which suits my current surplus best."),
        ("\U0001F331 Safest way to start investing", "What is the safest way for me to start investing a small monthly amount, given my current surplus?"),
    ],
}


# ---------------------------------------------------------------------------
# Page content renderers
# ---------------------------------------------------------------------------
def render_accounts_page(analyst, summary, breakdown_1mo, balance):
    payment_mode_1mo = analyst.payment_mode_breakdown(last_n_months=1)
    segment = st.session_state.current_user.get("segment", "Individual")
    acct_label = "SAVINGS ACCOUNT" if segment == "Individual" else "CURRENT ACCOUNT"
    st.markdown(f"""
    <div class="acct-card">
        <h3>{acct_label} &middot; {st.session_state.current_user['user_id']}</h3>
        <h1>Rs.{balance:,.2f}</h1>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Avg. Monthly Surplus (recent months)", f"Rs.{analyst.average_surplus():,.0f}")
    with c2:
        st.metric("This Month's Spend", f"Rs.{breakdown_1mo.sum():,.0f}")

    st.markdown("#### Spending Breakdown (This Month)")
    fig_pie = px.pie(values=breakdown_1mo.values, names=breakdown_1mo.index, hole=0.45,
                      color_discrete_sequence=px.colors.sequential.Tealgrn)
    fig_pie.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=320)
    st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("#### Income vs. Spend Trend")
    trend_df = summary.reset_index()
    trend_df["Month"] = trend_df["Month"].astype(str)
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=trend_df["Month"], y=trend_df["Income"], name="Income", line=dict(color="#0B3D2E")))
    fig_line.add_trace(go.Scatter(x=trend_df["Month"], y=trend_df["Spend"], name="Spend", line=dict(color="#D97757")))
    fig_line.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)
    st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("#### Spend by Payment Mode (This Month)")
    fig_bar = px.bar(x=payment_mode_1mo.index, y=payment_mode_1mo.values,
                      labels={"x": "Payment Mode", "y": "Amount (Rs.)"},
                      color=payment_mode_1mo.index,
                      color_discrete_sequence=px.colors.sequential.Tealgrn)
    fig_bar.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=280)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("#### Recent Card / UPI Activity")
    recent = analyst.recent_transactions(n=8)
    for _, row in recent.iterrows():
        sign = "+" if row["Type"] == "Credit" else "-"
        st.markdown(f"""<div class="txn-row">
            <span>{row['Category']} &middot; <span style="color:#8A96A3;">{row['Payment_Mode']}</span></span>
            <span>{sign}Rs.{row['Amount']:,.0f}</span></div>""", unsafe_allow_html=True)


def render_transfers_page(analyst):
    st.markdown("#### Transfer Funds (Demo)")
    st.caption("Simulated form - no real transfers are made in this prototype.")
    with st.form("transfer_form"):
        c1, c2 = st.columns(2)
        c1.text_input("Beneficiary Account Number", placeholder="XXXXXXXXXXXX")
        c1.text_input("IFSC Code", placeholder="IBKL0NEFT01")
        c2.number_input("Amount (Rs.)", min_value=0, step=100)
        c2.selectbox("Transfer Type", ["IMPS", "NEFT", "RTGS"])
        st.form_submit_button("Review Transfer", use_container_width=True, disabled=True)
    st.caption("Disabled in this prototype - the focus of this demo is the AI wealth advisory layer, not payment rails.")

    st.markdown("#### Recent Transfers (from your transaction history)")
    recent = analyst.recent_transactions(n=6)
    for _, row in recent.iterrows():
        sign = "+" if row["Type"] == "Credit" else "-"
        st.markdown(f"""<div class="txn-row"><span>{row['Category']} &middot; <span style="color:#8A96A3;">{row['Payment_Mode']}</span>
        - {row['Timestamp'].strftime('%d %b %Y')}</span><span>{sign}Rs.{row['Amount']:,.0f}</span></div>""", unsafe_allow_html=True)


def render_bills_page(analyst, breakdown_1mo):
    st.markdown("#### Upcoming Bills (Demo)")
    st.caption("Simulated bill list, identified from your recurring transaction categories this month.")
    # Keyword match (not exact names) so this works across every customer
    # segment's category naming - e.g. "Utility Bill Payment" (Individual) vs
    # "Business Insurance Premium" / "GST Payment" (enterprise segments).
    BILL_KEYWORDS = ["Bill", "EMI", "Insurance", "GST", "Lease", "Premium"]
    bill_items = [(cat, amt) for cat, amt in breakdown_1mo.items()
                  if any(kw.lower() in cat.lower() for kw in BILL_KEYWORDS)]
    if bill_items:
        for cat, amt in bill_items:
            st.markdown(f"""<div class="bill-row"><span>{cat}</span><span>Rs.{amt:,.0f} &nbsp;
            <span style="color:#16A34A;">Auto-pay eligible</span></span></div>""", unsafe_allow_html=True)
    else:
        st.caption("No recurring bill-type transactions found for this month.")
    st.button("Pay All Bills", use_container_width=True, disabled=True)
    st.caption("Disabled in this prototype - illustrative only.")


def render_investments_page(analyst, breakdown_1mo):
    st.markdown("#### Investment Overview (Demo)")
    # "Investment" as a single category no longer exists in the dataset -
    # FD/RD Contribution are the actual voluntary-savings categories now.
    invest_this_month = breakdown_1mo.get("FD Contribution", 0) + breakdown_1mo.get("RD Contribution", 0)
    c1, c2 = st.columns(2)
    c1.metric("FD/RD Contribution This Month", f"Rs.{invest_this_month:,.0f}")
    c2.metric("Avg. Monthly Surplus Available", f"Rs.{analyst.average_surplus():,.0f}")
    st.caption("Ask WealthAssist AI on the right for a personalized recommendation on where to put your surplus.")

    st.markdown("#### Quick FD/RD Calculator")
    c1, c2, c3 = st.columns(3)
    principal = c1.number_input("Amount (Rs.)", min_value=1000, value=10000, step=1000)
    rate = c2.number_input("Annual rate (%)", min_value=1.0, value=7.0, step=0.5)
    years = c3.number_input("Tenure (years)", min_value=1, value=3, step=1)
    maturity = principal * ((1 + rate / 100) ** years)
    st.info(f"Estimated maturity value: **Rs.{maturity:,.0f}** (simple compounding estimate, illustrative only)")


# ---------------------------------------------------------------------------
# Avatar + Chat panel (shared across all pages)
# ---------------------------------------------------------------------------
def render_avatar_panel(analyst, breakdown_1mo, breakdown_6mo, six_month_totals, flags):
    user = st.session_state.current_user
    with st.container(border=True):
        st.components.v1.html(
            get_avatar_html(st.session_state.avatar_url, speaking=st.session_state.avatar_speaking, height=200),
            height=210,
        )
        st.session_state.avatar_speaking = False  # pulse lasts one render cycle only
        st.markdown(f"""
        <div class="avatar-header">
            <div>
                <p class="avatar-name">WealthAssist AI</p>
                <p class="avatar-sub">Personal wealth avatar for {user['display_name'].split()[0]} &middot; {st.session_state.active_page}</p>
                <p class="avatar-sub" style="font-size: 10.5px; opacity: 1.0;">
                <span style="font-size: 10px;">\u26A0\uFE0F</span> Avatar yet to be modified and integrated with Voice.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        if flags:
            for f in flags:
                st.markdown(f'<div class="flag-card">\u26A0\ufe0f {f}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-flag-card">\u2705 No spending flags this month.</div>', unsafe_allow_html=True)

        st.markdown("**Quick questions**")

        def run_strategist(question=None):
            active_key, provider = get_active_api_key_and_provider()
            if not active_key:
                st.session_state.chat_history.append((
                    "assistant_error",
                    f"Please add your free {provider.capitalize()} API key in the sidebar first."
                ))
                return
            try:
                strategist = WealthStrategist(api_key=active_key, provider=provider)
                rec = strategist.recommend(
                    analyst.average_surplus(), breakdown_1mo, breakdown_6mo,
                    six_month_totals, flags, user_question=question,
                    kb_collection=st.session_state.kb_collection,
                )
                st.session_state.chat_history.append(("assistant_card", rec))
                st.session_state.avatar_speaking = True
            except Exception as e:
                st.session_state.chat_history.append(("assistant_error", f"Error calling the AI model ({provider}): {e}"))

        prompts = QUICK_PROMPTS.get(st.session_state.active_page, QUICK_PROMPTS["Accounts"])
        qcols = st.columns(2)
        for i, (label, q) in enumerate(prompts):
            if qcols[i % 2].button(label, use_container_width=True, key=f"quick_{st.session_state.active_page}_{i}"):
                st.session_state.chat_history.append(("user", q if q else label))
                run_strategist(q)

        st.markdown(f'<div class="disclaimer-box">\u26A0\uFE0F <b>Important:</b> {DISCLAIMER}</div>', unsafe_allow_html=True)

    return run_strategist


def render_chat_section(run_strategist):
    st.markdown("#### \U0001F4AC Chat with WealthAssist AI")
    history_box = st.container(height=280, border=True)
    with history_box:
        recent = st.session_state.chat_history[-12:]
        for i, (role, msg) in enumerate(recent):
            is_latest = (i == len(recent) - 1)
            if role == "user":
                with st.chat_message("user"):
                    st.write(msg)
            elif role == "assistant_error":
                with st.chat_message("assistant"):
                    st.error(msg)
            elif role == "assistant_card":
                with st.chat_message("assistant"):
                    st.write(msg.get("summary", ""))
                    if msg.get("reasoning"):
                        st.caption(msg["reasoning"])
                    for alloc in msg.get("allocations", []):
                        risk_class = "risk-low" if alloc.get("risk_level") == "Low" else "risk-medium"
                        st.markdown(f"""
                        <div class="rec-card">
                            <span class="rec-instrument">{alloc.get('instrument','')}</span>
                            <span class="risk-pill {risk_class}">{alloc.get('risk_level','')}</span>
                            <span class="rec-amount">Rs.{alloc.get('amount',0):,.0f}</span>
                            <div class="rec-why">{alloc.get('why','')}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    # Only synthesize audio for the latest response - avoids
                    # re-generating/re-embedding a player for every past
                    # message on every rerun. Speaks the FULL response
                    # (summary + reasoning + each allocation), not just the
                    # one-line summary, so nothing in the answer is silent.
                    if is_latest and msg.get("summary"):
                        speech_parts = [msg.get("summary", "")]
                        if msg.get("reasoning"):
                            speech_parts.append(msg["reasoning"])
                        for alloc in msg.get("allocations", []):
                            speech_parts.append(
                                f"{alloc.get('instrument', '')}: Rs {alloc.get('amount', 0):,.0f}. {alloc.get('why', '')}"
                            )
                        speech_text = " ".join(p for p in speech_parts if p)
                        try:
                            audio_bytes = text_to_speech_bytes(speech_text)
                            st.audio(audio_bytes, format="audio/mp3")
                        except Exception:
                            pass  # voice is optional - never block the text response

    user_msg = st.chat_input("Ask WealthAssist a question...")
    if user_msg:
        st.session_state.chat_history.append(("user", user_msg))
        run_strategist(user_msg)
        st.rerun()


# ---------------------------------------------------------------------------
# MAIN APP (after login)
# ---------------------------------------------------------------------------
def render_app():
    user = st.session_state.current_user

    with st.sidebar:
        st.markdown(f"### \U0001F464 {user['display_name']}")
        st.caption(f"Logged in as `{user['username']}`")
        if st.button("Log out"):
            st.session_state.logged_in = False
            st.session_state.chat_history = []
            st.rerun()
        st.divider()

        st.markdown(f"**Current section:** {st.session_state.active_page}")
        for page in PAGES:
            marker = "\u25CF" if page == st.session_state.active_page else "\u25CB"
            st.caption(f"{marker} {page}")
        st.divider()

        st.markdown("### \u2699\ufe0f AI Setup")
        st.session_state.ai_provider = st.radio(
            "AI Provider", ["Gemini", "Groq"],
            index=["Gemini", "Groq"].index(st.session_state.ai_provider),
            horizontal=True,
            help="Two providers so a quota limit on one doesn't stop the demo - "
                 "can switch here any time, mid-session.",
        )
        if st.session_state.ai_provider == "Gemini":
            st.session_state.api_key = st.text_input(
                "Gemini API Key",
                value=st.session_state.api_key,
                type="password",
                help="Create a free key at aistudio.google.com/apikey. Never share a "
                     "screenshot of this field - treat it exactly like a password.",
            )
        else:
            st.session_state.groq_api_key = st.text_input(
                "Groq API Key",
                value=st.session_state.groq_api_key,
                type="password",
                help="Create a free key at console.groq.com/keys. Never share a "
                     "screenshot of this field - treat it exactly like a password.",
            )
        st.caption("Used only for this session, never stored or logged.")

        # Build (or reuse) the vector DB of instrument docs once per Gemini key.
        # Gemini-only: the knowledge base uses Gemini's embedding model, so it
        # is skipped entirely on Groq (recommend() falls back to the static
        # instrument list automatically in that case - not a bug).
        if st.session_state.ai_provider == "Gemini" and st.session_state.api_key \
                and st.session_state.kb_key_used != st.session_state.api_key:
            try:
                st.session_state.kb_collection = kb.build_knowledge_base(st.session_state.api_key)
                st.session_state.kb_key_used = st.session_state.api_key
                st.caption("\u2705 Instrument knowledge base indexed (ChromaDB).")
            except Exception:
                st.session_state.kb_collection = None
                st.caption("\u26A0\ufe0f Vector DB unavailable this session - falling back to the static instrument list.")
        elif st.session_state.ai_provider == "Groq":
            st.session_state.kb_collection = None  # Groq path always uses the static list

        st.divider()

        st.markdown("### \U0001F9CD Avatar")
        with st.expander("Manage avatar options", expanded=not (st.session_state.avatar_slots["Avatar 1"] or st.session_state.avatar_slots["Avatar 2"])):
            st.session_state.avatar_slots["Avatar 1"] = st.text_input(
                "Avatar 1 - .glb URL",
                value=st.session_state.avatar_slots["Avatar 1"],
                placeholder="https://models.readyplayer.me/xxxx.glb",
                key="avatar_slot_1",
            )
            st.session_state.avatar_slots["Avatar 2"] = st.text_input(
                "Avatar 2 - .glb URL",
                value=st.session_state.avatar_slots["Avatar 2"],
                placeholder="https://models.readyplayer.me/yyyy.glb",
                key="avatar_slot_2",
            )
            st.caption("Leave a slot blank to hide it from the picker below.")

        available = {name: url for name, url in st.session_state.avatar_slots.items() if url.strip()}
        if available:
            choice = st.radio("Active avatar", options=list(available.keys()),
                               index=list(available.keys()).index(st.session_state.active_avatar)
                               if st.session_state.active_avatar in available else 0,
                               horizontal=True)
            st.session_state.active_avatar = choice
            st.session_state.avatar_url = available[choice]
        else:
            st.caption("No avatar URLs added yet - using the default demo avatar.")
            st.session_state.avatar_url = ""
        st.divider()

        st.markdown("### About this prototype")
        st.caption(
            "Independent hackathon prototype for IDBI Innovate 2026 (Problem "
            "Statement 1). Not affiliated with or built from IDBI Bank's real "
            "systems, data, or code. All users, balances, and transactions "
            "shown are synthetic."
        )

    analyst = BudgetAnalyst(txns_df, user["user_id"])
    summary = analyst.monthly_summary()
    breakdown_1mo = analyst.category_breakdown(last_n_months=1)
    breakdown_6mo = analyst.category_breakdown(last_n_months=6)
    six_month_totals = analyst.six_month_totals()
    flags = analyst.flags()
    balance = analyst.latest_balance()

    st.markdown("## \U0001F3E6 Digital Wealth Assistant \u2014 Prototype")
    st.caption("Simulated bank dashboard | Demo build for hackathon evaluation")
    render_nav()
    st.divider()

    col_main, col_avatar = st.columns([3, 2])

    with col_main:
        if st.session_state.active_page == "Accounts":
            render_accounts_page(analyst, summary, breakdown_1mo, balance)
        elif st.session_state.active_page == "Transfers":
            render_transfers_page(analyst)
        elif st.session_state.active_page == "Bill Payments":
            render_bills_page(analyst, breakdown_1mo)
        elif st.session_state.active_page == "Investments":
            render_investments_page(analyst, breakdown_1mo)

    with col_avatar:
        segment = st.session_state.current_user.get("segment", "Individual")
        if segment == "Individual":
            run_strategist = render_avatar_panel(analyst, breakdown_1mo, breakdown_6mo, six_month_totals, flags)
            render_chat_section(run_strategist)
        else:
            with st.container(border=True):
                st.markdown("#### \U0001F9CD WealthAssist AI")
                st.info(
                    f"AI wealth advisory is scoped to retail (Individual) accounts in this "
                    f"prototype. **{st.session_state.current_user['display_name']}** is a "
                    f"**{segment}** current account - you can still view its full transaction "
                    f"dashboard on the left, but personalized investment recommendations are "
                    f"only generated for individual customers."
                )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if st.session_state.logged_in:
    render_app()
else:
    render_login()