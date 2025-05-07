import json

def prediction_advisor_agent(predictions,transactions, client):
    """Generates actionable advice from budget predictions with robust error handling"""
    try:
        # Phase 1: Generate analysis with strict validation
        analysis = generate_analysis_phase(predictions,transactions, client)
        
        # Phase 2: Generate recommendation with strict validation
        recommendation = generate_recommendation_phase(predictions, client)
        
        return analysis, recommendation
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {str(e)}")
        # Return fallback responses if parsing fails
        return get_fallback_responses(predictions)
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return get_fallback_responses(predictions)

def generate_analysis_phase(predictions,transactions, client):
    """First phase with stricter prompt and validation"""
    data = []
    for txn in transactions:
        data.append((txn['date'],txn['type'],txn['reason'],txn['category'],txn['amount']))
    prompt = f"""
    STRICTLY follow these instructions to analyze financial predictions:

    Predictions Data: {json.dumps(predictions)}
    Last Month Transaction Data [(date, type, reason, category, amount )]: {data}

    Respond text should be in following format:
    observation1,observation2|daily_action|weekly_action|monthly_action|risk1,risk2|long_term_insight1,long_term_insight2

    RULES:
    1. Use direct commands ("Do X" not "Consider Y")
    2. Include numbers when possible
    3. Keep ALL responses under 2 sentences
    """
    
    completion = client.chat.completions.create(
        model="writer/palmyra-fin-70b-32k",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        temperature=0.1,  # Lower temperature for more predictable output
        response_format={"type": "json_object"}
    )
    
    res = completion.choices[0].message.content.replace("\n","").replace("\\","").replace("\n","").replace("\"","").split("|")
    print("Raw Analysis Output:", res)
    
    # Validate JSON structure before returning
    # parsed = json.loads(result)
    # required_keys = {"observations", "daily_actions", "weekly_actions", 
    #                 "monthly_actions", "risks", "long_term_insights"}
    # if not required_keys.issubset(parsed.keys()):
    #     raise ValueError("Missing required keys in analysis response")
    
    return {
        "observations": res[0].split(","),
        "daily_actions": res[1].split(","),
        "weekly_actions": res[2].split(","),
        "monthly_actions": res[3].split(","),
        "risks": res[4].split(","),
        "long_term_insights": res[5].split(",")
    }

def generate_recommendation_phase(predictions, client):
    """Second phase with stricter validation"""
    prompt = f"""
    Create ONE budget recommendation using this format ONLY:
    
    {{
        "time_period": "weekly|monthly",
        "amount": 123.45,
        "description": "Verb-starting 5-8 word instruction"
    }}

    Data: {json.dumps(predictions)}

    REQUIREMENTS:
    1. time_period must be exactly "weekly" or "monthly"
    2. amount must be positive with 2 decimal places
    3. description must start with a verb (Save, Reduce, etc.)
    4. No additional text outside the JSON
    5. JSON must be syntactically perfect
    """
    
    completion = client.chat.completions.create(
        model="writer/palmyra-fin-70b-32k",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=256,  # Fewer tokens for simpler response
        temperature=0.1,
        response_format={"type": "json_object"}
    )
    
    result = completion.choices[0].message.content
    print("Raw Recommendation Output:", result)
    
    # Validate JSON structure before returning
    parsed = json.loads(result)
    if not all(k in parsed for k in ["time_period", "amount", "description"]):
        raise ValueError("Missing required keys in recommendation")
    if parsed["time_period"] not in ["weekly", "monthly"]:
        raise ValueError("Invalid time_period value")
    
    return parsed

def get_fallback_responses(predictions):
    """Provides fallback responses when LLM fails"""
    fallback_analysis = {
        "observations": "Review your recent financial activity for patterns.",
        "daily_actions": "Track all expenses today to identify savings opportunities.",
        "weekly_actions": "Set aside 10% of weekly income for savings.",
        "monthly_actions": "Review monthly subscriptions and cancel unused services.",
        "risks": "Unplanned expenses could disrupt your cash flow.",
        "long_term_insights": "Consistent saving will build financial resilience."
    }
    
    fallback_recommendation = {
        "time_period": "weekly",
        "amount": 100.00,
        "description": "Save 10% of weekly income automatically"
    }
    
    return fallback_analysis, fallback_recommendation