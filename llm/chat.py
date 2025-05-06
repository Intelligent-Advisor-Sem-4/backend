def chat_with_llm(prompt: str, client):
    try:
        completion = client.chat.completions.create(
            model="writer/palmyra-fin-70b-32k",
            messages=[{"role": "user", "content": prompt+" Note- Assume that you are a financial advisor. Only answer the questions related to finance. Other questions should be neglected"}],
            temperature=0.2,
            top_p=0.7,
            max_tokens=1024
            # stream=False by default
        )
        return completion.choices[0].message.content
        
    except Exception as e:
        raise ValueError(f"LLM processing error: {str(e)}")