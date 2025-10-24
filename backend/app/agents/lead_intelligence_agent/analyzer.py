# backend/app/agents/lead_intelligence_agent/analyzer.py

"""
Lead Intelligence Analyzer
Provides sentiment analysis and intent extraction for customer interactions
"""

# Sentiment keywords
POSITIVE_KEYWORDS = [
    "interested", "love", "perfect", "excellent", "amazing", "great", "wonderful",
    "excited", "looking forward", "impressive", "beautiful", "fantastic"
]

NEGATIVE_KEYWORDS = [
    "expensive", "too much", "not sure", "concerned", "worried", "hesitant",
    "maybe later", "thinking about it", "budget", "afford"
]

NEUTRAL_KEYWORDS = [
    "information", "details", "options", "compare", "research", "learn more"
]

# Intent keywords
INTENT_KEYWORDS = {
    "test_drive": [
        "test drive", "drive the car", "try it out", "test it", "take it for a spin",
        "experience the vehicle", "feel the car"
    ],
    "pricing": [
        "price", "cost", "how much", "payment", "financing", "afford",
        "monthly payment", "down payment", "total cost", "pricing"
    ],
    "appointment": [
        "schedule", "appointment", "visit", "come by", "showroom",
        "meet", "when can I", "availability"
    ],
    "purchase_ready": [
        "buy now", "ready to purchase", "want to buy", "make a deal",
        "sign the papers", "close the deal", "ready to proceed"
    ],
    "comparison": [
        "compare", "difference between", "versus", "vs", "which is better",
        "alternative", "other options"
    ],
    "features": [
        "features", "specifications", "specs", "what does it have",
        "include", "comes with", "standard", "options"
    ],
    "trade_in": [
        "trade in", "trade-in", "current car", "sell my car",
        "exchange", "part exchange"
    ],
    "service": [
        "maintenance", "service", "warranty", "repair",
        "servicing", "after sales"
    ]
}


def analyze_conversation_sentiment(text: str) -> str:
    """
    Analyze the sentiment of a conversation.
    Returns: 'Positive', 'Negative', or 'Neutral'
    """
    if not text:
        return 'Neutral'
    
    text_lower = text.lower()
    
    positive_count = sum(1 for keyword in POSITIVE_KEYWORDS if keyword in text_lower)
    negative_count = sum(1 for keyword in NEGATIVE_KEYWORDS if keyword in text_lower)
    
    # Simple scoring logic
    if positive_count > negative_count and positive_count > 0:
        return 'Positive'
    elif negative_count > positive_count and negative_count > 0:
        return 'Negative'
    else:
        return 'Neutral'


def extract_key_intents(text: str) -> list:
    """
    Extract key intents from conversation text.
    Returns: List of intent strings (e.g., ['test_drive', 'pricing'])
    """
    if not text:
        return []
    
    text_lower = text.lower()
    detected_intents = []
    
    for intent_type, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                detected_intents.append(intent_type)
                break  # Only add each intent once
    
    return detected_intents


def calculate_engagement_score(text: str) -> int:
    """
    Calculate an engagement score (0-100) based on conversation quality.
    Higher scores indicate more engaged customers.
    """
    if not text:
        return 0
    
    score = 0
    text_lower = text.lower()
    
    # Length indicates engagement (longer conversations = more interested)
    word_count = len(text.split())
    if word_count > 100:
        score += 30
    elif word_count > 50:
        score += 20
    else:
        score += 10
    
    # Multiple intents show deeper interest
    intents = extract_key_intents(text)
    score += min(len(intents) * 15, 40)  # Cap at 40 points
    
    # Positive sentiment adds points
    sentiment = analyze_conversation_sentiment(text)
    if sentiment == 'Positive':
        score += 20
    elif sentiment == 'Neutral':
        score += 10
    
    # Questions indicate engagement
    question_count = text.count('?')
    score += min(question_count * 5, 10)  # Cap at 10 points
    
    return min(score, 100)  # Cap at 100


def extract_vehicle_preferences(text: str) -> dict:
    """
    Extract vehicle preferences mentioned in the conversation.
    Returns: Dict with preferences (brand, model, price_range, etc.)
    """
    text_lower = text.lower()
    preferences = {
        "brands": [],
        "models": [],
        "price_range": None,
        "features_mentioned": []
    }
    
    # Luxury brands
    brands = ["rolls-royce", "bentley", "ferrari", "lamborghini", "porsche", 
              "maserati", "aston martin", "mclaren", "bugatti", "mercedes", "bmw"]
    for brand in brands:
        if brand in text_lower:
            preferences["brands"].append(brand.title())
    
    # Popular luxury models
    models = ["phantom", "cullinan", "ghost", "continental", "488", "aventador",
              "huracan", "911", "cayenne", "panamera", "db11", "vantage"]
    for model in models:
        if model in text_lower:
            preferences["models"].append(model.title())
    
    # Price indications
    if any(word in text_lower for word in ["crore", "lakh", "million"]):
        if "2 crore" in text_lower or "20000000" in text_lower:
            preferences["price_range"] = "2-5 Crores"
        elif "5 crore" in text_lower or "50000000" in text_lower:
            preferences["price_range"] = "5-10 Crores"
        elif "10 crore" in text_lower:
            preferences["price_range"] = "10+ Crores"
    
    # Features
    features = ["convertible", "suv", "sedan", "coupe", "electric", "hybrid",
                "all-wheel drive", "awd", "v8", "v12", "turbo", "supercharged"]
    for feature in features:
        if feature in text_lower:
            preferences["features_mentioned"].append(feature.title())
    
    return preferences


def generate_conversation_insights(text: str) -> dict:
    """
    Generate comprehensive insights from a conversation.
    This is the main function to call for complete analysis.
    """
    return {
        "sentiment": analyze_conversation_sentiment(text),
        "intents": extract_key_intents(text),
        "engagement_score": calculate_engagement_score(text),
        "vehicle_preferences": extract_vehicle_preferences(text),
        "word_count": len(text.split()) if text else 0,
        "question_count": text.count('?') if text else 0
    }


def prioritize_leads(customers_data: list) -> list:
    """
    Prioritize a list of leads based on their engagement and status.
    Input: List of dicts with customer data and conversation text
    Output: Sorted list with priority scores
    """
    scored_customers = []
    
    for customer in customers_data:
        text = customer.get('last_conversation', '')
        customer_type = customer.get('customer_type', 'Prospect')
        
        # Calculate base score from engagement
        engagement = calculate_engagement_score(text)
        
        # Adjust based on customer type
        type_multiplier = {
            'Hot Lead': 1.5,
            'Warm Lead': 1.2,
            'Prospect': 1.0,
            'Cold Lead': 0.8
        }
        
        multiplier = type_multiplier.get(customer_type, 1.0)
        priority_score = engagement * multiplier
        
        scored_customers.append({
            **customer,
            'priority_score': priority_score,
            'engagement_score': engagement
        })
    
    # Sort by priority score (highest first)
    return sorted(scored_customers, key=lambda x: x['priority_score'], reverse=True)


def recommend_next_action(customer_data: dict) -> str:
    """
    Recommend the next best action for a customer based on their data.
    """
    text = customer_data.get('last_conversation', '')
    customer_type = customer_data.get('customer_type', 'Prospect')
    days_since_contact = customer_data.get('days_since_last_contact', 0)
    
    intents = extract_key_intents(text)
    sentiment = analyze_conversation_sentiment(text)
    
    # Decision tree for recommendations
    if customer_type == 'Hot Lead':
        if 'purchase_ready' in intents:
            return "URGENT: Schedule closing meeting within 24 hours"
        elif 'test_drive' in intents:
            return "HIGH PRIORITY: Confirm test drive appointment immediately"
        elif days_since_contact > 2:
            return "FOLLOW UP: Contact within 4 hours - hot lead cooling"
        else:
            return "MONITOR: Prepare for next interaction"
    
    elif customer_type == 'Warm Lead':
        if 'test_drive' in intents:
            return "Schedule test drive within 48 hours"
        elif 'pricing' in intents:
            return "Send detailed pricing and financing options"
        elif days_since_contact > 5:
            return "Send nurture email with new inventory updates"
        else:
            return "Continue regular follow-up in 3 days"
    
    elif customer_type == 'Prospect':
        if sentiment == 'Positive':
            return "Send welcome email with showroom invitation"
        elif 'information' in text.lower():
            return "Send comprehensive brochure and schedule call"
        else:
            return "Add to nurture campaign - weekly updates"
    
    else:  # Cold Lead
        if days_since_contact < 30:
            return "Add to quarterly newsletter"
        else:
            return "Archive - re-engage only if customer initiates contact"