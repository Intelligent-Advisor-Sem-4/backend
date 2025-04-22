import json
def prediction_advisor_agent(predictions,client):
    """Generates actionable advice from budget predictions"""
    prompt = f"""
Analyze these financial predictions and provide concise responses (MAX 2 SENTENCES PER SECTION):

Predictions Data: {predictions}

Respond in JSON format with these exact keys:
{{
    "observations": "Cash flow observation in 2 sentences MAX",
    "daily_actions": "One actionable step for today in MAX 2 sentences",
    "weekly_actions": "One weekly action in MAX 2 sentences",
    "monthly_actions": "One monthly action in MAX 2 sentences",
    "risks": "Top risk warning in MAX 2 sentences",
    "long_term_insights": "Key long-term impact in MAX 2 sentences"
}}

    Rules:
    1. Use actionable language ("Do X" not "You might consider Y")
    2. Prioritize numeric targets in goals
    3. Omit filler phrases like "based on the data"
    4. MAke sure to keep the json format properly (Priority HIGH)
    5. MAX 2 SENTENCES PER SECTION (Priority HIGH)
    """
    completion = client.chat.completions.create(
        model="writer/palmyra-fin-70b-32k",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        temperature=0.2,  # Slightly higher for creative suggestions
        response_format={"type": "json_object"}
    )
    res = completion.choices[0].message.content
    print(res)
    res = json.loads(res)
    print(res)

    prompt = """
    Generate one budget recommendation based on financial predictions. Respond in strict JSON format only.
    Analyze these data
    Predictions Data: """ + str(predictions) + """
    Generate a JSON structure:
    {
            "time_period": "weekly or monthly only",
            "amount": "positive number with 2 decimal places",
            "description": "actionable instructions (use 5-6 sentences)"     
    }

Strict Requirements:
1. Output must be valid JSON that parses successfully
2. Exactly one goals - no more, no less
3. goal must have all 3 fields (time_period, amount, description)
4. time_period must be either "weekly" or "monthly" exactly
5. amount must be positive with exactly 2 decimal places (e.g. 250.00)
6. description must be 5-8 words starting with a verb (e.g. "Save", "Reduce")
7. No additional text or explanations outside the JSON structure
8. Field names must be exactly as shown (lowercase, no typos)
"""

    completion = client.chat.completions.create(
        model="writer/palmyra-fin-70b-32k",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    res2 = completion.choices[0].message.content
    print(res2)
    res2 = json.loads(res2)
    print(res2)
    return res,res2