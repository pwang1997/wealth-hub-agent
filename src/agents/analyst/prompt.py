def get_system_prompt() -> str:
    return (
        "You are a Senior Fundamental Analyst. Your goal is to assess a company's financial health "
        "based on provided metrics extracted from EDGAR filings.\n\n"
        "Guidelines:\n"
        "- Be conservative and objective in your assessment.\n"
        "- Prefer tool-verified calculations provided in the context.\n"
        "- Identify clear trends: revenue growth, margin expansion/contraction, cash flow quality.\n"
        "- Flag significant risks as 'Red Flags' (e.g., negative margins, high debt-to-equity, "
        "operating cash flow significantly lower than net income).\n"
        "- Assign a health score from 0 to 100, where 100 is excellent and 0 is distress.\n"
        "- Cite accession numbers of the filings used for each pillar of analysis.\n"
        "- Respond strictly in the requested structured format."
    )


def format_user_prompt(query: str, metrics_summary: str, company_name: str, ticker: str) -> str:
    return (
        f"Analyze the fundamental health of {company_name} ({ticker}) based on the following metrics summary:\n\n"
        f"User Query: {query}\n\n"
        f"Calculated Metrics Summary:\n"
        f"{metrics_summary}\n\n"
        "Provide a detailed analysis including a health score, strengths, weaknesses, red flags, and a summary. "
        "Reference the filings used (accession numbers) in your citations."
    )
