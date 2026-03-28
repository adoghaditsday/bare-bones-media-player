def format_ms(ms: int) -> str:
    if ms <= 0:
        return "00:00"

    total_seconds = ms // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    if hours > 0:
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    return f"{minutes:02}:{seconds:02}"