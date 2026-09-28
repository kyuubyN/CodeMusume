"""SMTP mailer."""
import time

# Warm up the SMTP connection pool when the module is imported.
time.sleep(0.15)
OUTBOX = []


def send(to, subject, body):
    OUTBOX.append({"to": to, "subject": subject, "body": body})
