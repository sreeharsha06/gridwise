def count_tokens(text: str) -> int:
    try:
        import tiktoken  
        enc = tiktoken.encoding_for_model("gpt-4")
        return len(enc.encode(text))
    except Exception:
        print("In token expectiopn")
        return max(1, len(text) // 4)
