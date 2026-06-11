from datetime import datetime, timedelta

def format_notification_time(created_at: datetime):
    now = datetime.utcnow()
    diff = now - created_at
    
    if diff < timedelta(minutes=1):
        return "Just now"
    elif diff < timedelta(hours=1):
        return f"{int(diff.total_seconds() // 60)} min ago"
    elif diff < timedelta(days=1):
        return f"{int(diff.total_seconds() // 3600)} hour ago"
    elif diff < timedelta(days=2):
        return "Yesterday"
    else:
        return created_at.strftime("%d %b %Y")