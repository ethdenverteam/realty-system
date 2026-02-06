"""
Rate limiter for Telethon to prevent account blocking
Strict limits: 1 message per minute, 60 messages per hour
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict
import threading

# Global rate limiter state
_rate_limiter_lock = threading.Lock()
_message_times: Dict[str, List[float]] = defaultdict(list)  # phone -> list of message timestamps


def can_send_message(phone: str) -> tuple[bool, float]:
    """
    Check if we can send a message for this phone number
    Returns: (can_send, wait_seconds)
    """
    with _rate_limiter_lock:
        now = time.time()
        times = _message_times[phone]
        
        # Remove old timestamps (older than 1 hour)
        one_hour_ago = now - 3600
        times[:] = [t for t in times if t > one_hour_ago]
        
        # Check hourly limit (60 messages per hour)
        if len(times) >= 60:
            # Find the oldest message in the last hour
            oldest_in_hour = min(times) if times else now
            wait_seconds = 3600 - (now - oldest_in_hour)
            if wait_seconds > 0:
                return (False, wait_seconds)
        
        # Check per-minute limit (1 message per minute)
        if times:
            last_message_time = max(times)
            time_since_last = now - last_message_time
            if time_since_last < 60:
                wait_seconds = 60 - time_since_last
                return (False, wait_seconds)
        
        return (True, 0.0)


def record_message_sent(phone: str):
    """Record that a message was sent"""
    with _rate_limiter_lock:
        now = time.time()
        _message_times[phone].append(now)
        
        # Clean up old entries (keep only last hour)
        one_hour_ago = now - 3600
        _message_times[phone] = [t for t in _message_times[phone] if t > one_hour_ago]


def wait_if_needed(phone: str) -> float:
    """
    Wait if needed before sending message
    Returns: actual wait time in seconds
    """
    can_send, wait_seconds = can_send_message(phone)
    if not can_send and wait_seconds > 0:
        time.sleep(wait_seconds)
        return wait_seconds
    return 0.0


def get_rate_limit_status(phone: str) -> dict:
    """Get current rate limit status for phone"""
    with _rate_limiter_lock:
        now = time.time()
        times = _message_times[phone]
        
        # Remove old timestamps
        one_hour_ago = now - 3600
        times[:] = [t for t in times if t > one_hour_ago]
        
        messages_in_hour = len(times)
        can_send, wait_seconds = can_send_message(phone)
        
        # Calculate time until next available slot
        next_available = None
        if times:
            last_message_time = max(times)
            time_since_last = now - last_message_time
            if time_since_last < 60:
                next_available = datetime.utcnow() + timedelta(seconds=60 - time_since_last)
        
        return {
            'can_send': can_send,
            'wait_seconds': wait_seconds,
            'messages_in_hour': messages_in_hour,
            'messages_remaining': 60 - messages_in_hour,
            'next_available': next_available.isoformat() if next_available else None
        }

