"""Sending letters through the mailbox on the site's domain: SMTP over SSL, no mailing service.

Settings are MAIL_* in config.py. Without MAIL_HOST (development) nothing is sent:
only the subject is written to the log (the whole letter only with MAIL_LOG_BODY=1,
links in letters carry tokens), and in tests a letter goes to app.extensions["mail_outbox"].
The recipient's address never goes to the log.
Letters are plain text: no pictures and no external resources.
"""

import smtplib
import ssl
import threading
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

from flask import current_app


class MailError(Exception):
    """The letter was not sent. The reason is already in the log."""


def send(to, subject, body):
    config = current_app.config
    if not config["MAIL_HOST"]:
        if current_app.testing:
            current_app.extensions.setdefault("mail_outbox", []).append(
                {"to": to, "subject": subject, "body": body},
            )
        elif config["MAIL_LOG_BODY"]:
            current_app.logger.warning("Mail is not configured, letter to %s:\n%s\n%s", to, subject, body)
        else:
            current_app.logger.warning("Mail is not configured, letter \"%s\" was not sent", subject)
        return

    message = EmailMessage()
    # formataddr encodes a non-ASCII sender name for the header.
    message["From"] = formataddr(parseaddr(config["MAIL_FROM"] or config["MAIL_USERNAME"]))
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        with smtplib.SMTP_SSL(
            config["MAIL_HOST"], config["MAIL_PORT"],
            timeout=config["MAIL_TIMEOUT"], context=ssl.create_default_context(),
        ) as smtp:
            smtp.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
            smtp.send_message(message)
    except (smtplib.SMTPException, OSError) as e:
        # Only the error type, without its text and traceback: SMTPRecipientsRefused
        # and others carry the recipient's address, and the logs keep no personal data.
        current_app.logger.error("Letter \"%s\" was not sent: %s", subject, type(e).__name__)
        raise MailError() from e


def send_later(to, subject, body):
    """Sends the letter in a background thread; an error is only logged.

    The response does not wait for the mail server, and its time does not reveal
    whether a letter was sent at all (password reset for an unknown account).
    In tests the letter is sent right away, so the outbox is filled before the response.
    """
    app = current_app._get_current_object()

    def run():
        with app.app_context():
            try:
                send(to, subject, body)
            except MailError:
                pass

    if app.testing:
        run()
    else:
        threading.Thread(target=run, daemon=True).start()
