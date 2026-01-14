def get_system_prompt() -> str:
    return (
        "You are a News Analyst AI. Your role is to synthesize market news sentiment "
        "into a coherent narrative. You will be provided with a set of news items "
        "and calculated sentiment scores. Your goal is to explain the rationale "
        "behind the overall sentiment, highlighting the key drivers and any "
        "contradictory signals."
    )


def format_synthesis_prompt(
    query: str,
    overall_score: float,
    overall_label: str,
    top_headlines: list[str],
    ticker_summaries: str,
) -> str:
    headlines_str = "\n".join([f"- {h}" for h in top_headlines])
    return (
        f"Query: {query}\n\n"
        f"Overall Sentiment Score: {overall_score} ({overall_label})\n\n"
        "Key Headlines:\n"
        f"{headlines_str}\n\n"
        "Per-Ticker Rollups:\n"
        f"{ticker_summaries}\n\n"
        "Provide a concise qualitative rationale (2-3 sentences) summarizing "
        "why the sentiment is labeled as it is, citing the most influential news."
    )
