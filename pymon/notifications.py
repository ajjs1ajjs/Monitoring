"""Notification dispatching for PyMon"""

import json
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class NotificationDispatcher:
    def __init__(self, config=None):
        self.config = config

    def send_telegram(self, message: str, bot_token: str, chat_id: str):
        """Send a message via Telegram Bot API"""
        if not bot_token or not chat_id:
            return False
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            return False

    def send_discord(self, message: str, webhook_url: str):
        """Send a message via Discord Webhook"""
        if not webhook_url:
            return False
        
        payload = {
            "content": None,
            "embeds": [
                {
                    "title": "PyMon Alert",
                    "description": message,
                    "color": 15158332  # Red
                }
            ]
        }
        try:
            resp = requests.post(webhook_url, json=payload, timeout=10)
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Discord notification failed: {e}")
            return False

    def dispatch(self, alert_name: str, message: str, channels: dict):
        """
        Dispatch alert to various channels based on configuration.
        channels: {
            "telegram": {"bot_token": "...", "chat_id": "..."},
            "discord": {"webhook_url": "..."},
        }
        """
        results = {}
        
        if "telegram" in channels:
            tg = channels["telegram"]
            results["telegram"] = self.send_telegram(
                f"<b>🚨 ALERT: {alert_name}</b>\n\n{message}",
                tg.get("bot_token"),
                tg.get("chat_id")
            )
            
        if "discord" in channels:
            ds = channels["discord"]
            results["discord"] = self.send_discord(
                message,
                ds.get("webhook_url")
            )
            
        return results

dispatcher = NotificationDispatcher()
