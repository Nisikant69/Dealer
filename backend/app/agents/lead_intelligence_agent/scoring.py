# This is a simple, rule-based keyword scorer. It's deterministic and testable.
# We are not using the LLM yet because it's slower and adds complexity.
# Start simple, prove the workflow, then enhance.

# Define keywords that indicate lead temperature. These are your business rules.
HOT_KEYWORDS = [
    "buy now", "ready to purchase", "schedule test drive", "phantom", "cullinan",
    "bentley", "ferrari", "urgent", "book appointment", "quote needed"
]
WARM_KEYWORDS = [
    "interested", "more information", "pricing", "financing", "options",
    "compare models", "availability"
]
COLD_KEYWORDS = ["just looking", "researching", "future", "maybe later", "not serious"]

def score_lead_from_text(text_input: str) -> str:
    """
    Analyzes input text for keywords to determine lead status.
    Returns 'Hot Lead', 'Warm Lead', or 'Cold Lead'.
    This is a naive implementation and should be refined.
    """
    if not text_input:
        return 'Cold Lead'  # No text means a cold lead by default.

    text_lower = text_input.lower()

    # Priority matters. A lead is hot even if they also use warm keywords.
    if any(keyword in text_lower for keyword in HOT_KEYWORDS):
        print("Scoring Logic: Found HOT keywords.")
        return 'Hot Lead'

    if any(keyword in text_lower for keyword in WARM_KEYWORDS):
        print("Scoring Logic: Found WARM keywords.")
        return 'Warm Lead'

    if any(keyword in text_lower for keyword in COLD_KEYWORDS):
        print("Scoring Logic: Found COLD keywords.")
        return 'Cold Lead'

    # If text exists but contains no specific keywords, it's an inquiry worth following up.
    print("Scoring Logic: No specific keywords found, defaulting to WARM.")
    return 'Warm Lead'
