"""Notification dispatching for PyMon"""

import logging

import httpx

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
            with httpx.Client() as client:
                resp = client.post(url, json=payload, timeout=10)
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
            with httpx.Client() as client:
                resp = client.post(webhook_url, json=payload, timeout=10)
                resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Discord notification failed: {e}")
            return False

    def send_teams(self, message: str, webhook_url: str):
        """Send a message via MS Teams Webhook"""
        if not webhook_url:
            return False

        payload = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Medium",
                                "weight": "Bolder",
                                "text": "PyMon Alert"
                            },
                            {
                                "type": "TextBlock",
                                "text": message,
                                "wrap": True
                            }
                        ],
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.0"
                    }
                }
            ]
        }
        try:
            with httpx.Client() as client:
                resp = client.post(webhook_url, json=payload, timeout=10)
                resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"MS Teams notification failed: {e}")
            return False

    def send_email(self, message: str, subject: str, config: dict):
        """Send a message via SMTP"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        smtp_server = config.get("smtp_server")
        smtp_port = config.get("smtp_port", 587)
        smtp_user = config.get("smtp_user")
        smtp_pass = config.get("smtp_pass")
        email_to = config.get("email_to")

        if not all([smtp_server, smtp_user, email_to]):
            return False

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = email_to
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'html'))

        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if smtp_pass:
                    server.starttls()
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            return False

    def dispatch(self, alert_name: str, message: str, channels: dict):
        """
        Dispatch alert to various channels based on configuration.
        channels: {
            "telegram": {"bot_token": "...", "chat_id": "..."},
            "discord": {"webhook_url": "..."},
            "teams": {"webhook_url": "..."},
            "email": {"smtp_server": "...", ...}
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

        if "teams" in channels:
            tm = channels["teams"]
            results["teams"] = self.send_teams(
                message,
                tm.get("webhook_url")
            )

        if "email" in channels:
            em = channels["email"]
            results["email"] = self.send_email(
                message,
                f"PyMon Alert: {alert_name}",
                em
            )

        return results

dispatcher = NotificationDispatcher()
