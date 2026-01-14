def get_system_prompt() -> str:
    return (
        "You are an expert financial research analyst responsible for synthesizing disparate "
        "data points into a cohesive, professional investment report. You must weave together "
        "long-term fundamental health with short-term market sentiment to provide context "
        "for an investor.\n\n"
        "Your output must be a valid JSON object with the following fields:\n"
        "- 'composed_analysis': A cohesive and professional synthesis of the input data.\n"
        "- 'warnings': A list of strings for any data gaps or risks."
    )


def format_synthesis_prompt(
    ticker: str,
    fundamental_summary: str,
    fundamental_score: int,
    news_rationale: str,
    news_score: float,
    objectives: str,
) -> str:
    return f"""### Reporting Task for {ticker}
Objectives identified: {objectives}

### Input: Fundamental Analysis (Health Score: {fundamental_score}/100)
{fundamental_summary}

### Input: News Sentiment Analysis (Sentiment Score: {news_score:.4f})
{news_rationale}

### Instructions
1. Synthesize the above inputs into a single, professional analysis.
2. The analysis must explain HOW the fundamental health and market sentiment interact.
3. Contrast long-term value (Fundamentals) with short-term headwinds or tailwinds (News).
4. Do NOT provide a buy/sell/hold recommendation. Focus purely on the synthesis of information.
"""
