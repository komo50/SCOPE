import streamlit as st
import yfinance as yf
import requests
import re
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import google.generativeai as genai

# 🔐 Set Gemini API Key
genai.configure(api_key="AIzaSyDozk5mXZXB-cI8szc1DxpRK7fhs17GTFw")  # Replace this with your actual Gemini API key

# --- Streamlit Header ---
st.title("🧠 AI Investment Screener")
st.caption("Built by Sam Kominowski")

ticker_input = st.text_input("Enter stock ticker (e.g. AAPL, TSLA):")
company_name = st.text_input("Enter company name (for news search):")

# --- Helper Functions ---
def contains_whole_word(text, keywords):
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in keywords)

def summarize_regulatory_risk_gemini(articles, company):
    formatted_articles = "\n".join([f"- {a['title']} ({a['url']})" for a in articles])
    prompt = f"""
You are a venture capital analyst. Below are recent news headlines about {company}, each with its link.
Summarize whether any of these suggest regulatory risks or government support for the company or its industry.
Be specific, neutral in tone, and limit to 2–3 sentences.

Headlines:
{formatted_articles}
"""
    model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
    response = model.generate_content(prompt)
    return response.text.strip()

def summarize_financials_with_llm(info, company):
    prompt = f"""
You are a venture capital analyst evaluating {company}. Here are some financial metrics:

- Current Ratio: {info.get("currentRatio")}
- Gross Margin: {info.get("grossMargins")}
- Debt-to-Equity Ratio: {info.get("debtToEquity")}

Write a concise summary of the company's financial health in 2-3 sentences. Be specific and neutral in tone.
"""
    model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
    response = model.generate_content(prompt)
    return response.text.strip()

def summarize_sentiment_with_llm(articles, company):
    formatted_articles = "\n".join([f"- {a['title']} ({a['url']})" for a in articles])
    prompt = f"""
You're a venture capital analyst. Summarize recent market sentiment around {company} based on the following headlines in 200 words or less.
Mention the general tone and any emerging themes or concerns.

Headlines:
{formatted_articles}
"""
    model = genai.GenerativeModel("models/gemini-1.5-flash-latest")
    response = model.generate_content(prompt)
    return response.text.strip()

# --- Main App Logic ---
if st.button("Analyze") and ticker_input and company_name:
    # --- Financials ---
    ticker = yf.Ticker(ticker_input)
    info = ticker.info
    current_ratio = info.get("currentRatio")
    gross_margin = info.get("grossMargins")
    de_ratio = info.get("debtToEquity")

    finance_issues = []
    if current_ratio is not None and current_ratio < 1.5:
        finance_issues.append("Low liquidity (Current Ratio < 1.5)")
    if gross_margin is not None and gross_margin < 0.4:
        finance_issues.append("Weak profitability (Gross Margin < 40%)")
    if de_ratio is not None and de_ratio >= 1:
        finance_issues.append("High leverage (Debt-to-Equity ≥ 1)")

    finance_health = "✅ Healthy" if not finance_issues else "⚠️ Needs Review"
    st.subheader("📈 Financial Health")
    st.write(f"**Result:** {finance_health}")
    for issue in finance_issues:
        st.write("•", issue)

    with st.spinner("Summarizing financials..."):
        finance_summary = summarize_financials_with_llm(info, company_name)
    st.subheader("🧠 LLM Financial Summary")
    st.write(finance_summary)

    # --- News Sentiment ---
    analyzer = SentimentIntensityAnalyzer()
    GNEWS_API_KEY = "831abe6fd38794ef8465616f6ba2a0ff"  # Replace this with your GNews API key
    url = f"https://gnews.io/api/v4/search?q={company_name}&lang=en&token={GNEWS_API_KEY}"
    response = requests.get(url)
    data = response.json()
    articles = data.get("articles", [])

    scores = []
    for article in articles:
        score = analyzer.polarity_scores(article["title"])["compound"]
        scores.append(score)

    if scores:
        avg_score = sum(scores) / len(scores)
        sentiment_result = (
            "✅ Positive" if avg_score > 0.2 else
            "❌ Negative" if avg_score < -0.2 else
            "🟰 Neutral"
        )
    else:
        sentiment_result = "❌ No news found"

    st.subheader("📰 Market Sentiment")
    st.write(f"**Result:** {sentiment_result}")
    if scores:
        st.write(f"Average sentiment score: {round(avg_score, 3)}")

    with st.spinner("Summarizing market sentiment..."):
        sentiment_summary = summarize_sentiment_with_llm(articles[:5], company_name)
    st.subheader("🧠 LLM Sentiment Summary")
    st.write(sentiment_summary)

    # --- Regulatory Scan ---
    regulatory_flags = []
    risk_keywords = ["investigation", "ban", "lawsuit", "probe", "fine", "regulation", "antitrust", "ftc", "sec", "doj"]
    support_keywords = ["subsidy", "approved", "grant", "funding", "support", "incentive", "chips act"]

    for article in articles:
        title = article["title"].lower()
        if contains_whole_word(title, risk_keywords):
            regulatory_flags.append("❌ " + article["title"])
        elif contains_whole_word(title, support_keywords):
            regulatory_flags.append("✅ " + article["title"])

    if any("❌" in r for r in regulatory_flags):
        regulatory_result = "❌ Risk flagged"
    elif any("✅" in r for r in regulatory_flags):
        regulatory_result = "✅ Favorable mention"
    else:
        regulatory_result = "🟰 No major regulatory signal"

    st.subheader("📋 Regulatory Environment")
    st.write(f"**Result:** {regulatory_result}")
    for flag in regulatory_flags[:3]:
        st.write("•", flag)

    with st.spinner("Analyzing regulatory risk with Gemini..."):
        regulatory_summary = summarize_regulatory_risk_gemini(articles[:5], company_name)
    st.subheader("🧠 LLM Risk Summary")
    st.write(regulatory_summary)

    # --- Final Ruling ---
    if (
        finance_health == "✅ Healthy"
        and sentiment_result in ["✅ Positive", "🟰 Neutral"]
        and regulatory_result in ["✅ Favorable mention", "🟰 No major regulatory signal"]
    ):
        ruling = "✅ INVEST"
    elif "❌" in (finance_health, sentiment_result, regulatory_result):
        ruling = "❌ AVOID"
    else:
        ruling = "⚠️ WATCHLIST"

    st.markdown("---")
    st.subheader("📈 FINAL RULING")
    st.markdown(f"### {ruling}")

    if ruling == "⚠️ WATCHLIST":
        reasons = []
        if finance_health == "⚠️ Needs Review":
            reasons.append("financial metrics triggered concern")
        if sentiment_result == "❌ Negative":
            reasons.append("negative market sentiment")
        if sentiment_result == "❌ No news found":
            reasons.append("no recent news available")
        if regulatory_result == "❌ Risk flagged":
            reasons.append("negative regulatory signal")
        st.write("**Reason:**", ", ".join(reasons).capitalize())