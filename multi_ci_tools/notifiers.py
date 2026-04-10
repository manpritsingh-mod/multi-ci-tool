"""Notification module for sending build summaries via multiple channels.

Implements console, Slack, and email notifiers for pipeline result delivery.
All notifications are best-effort; failures are logged but never crash the pipeline.
"""

import json
import logging
import os
import smtplib
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from multi_ci_tools.types import PipelineResult

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NotifierConfig:
    """Configuration for notifiers sourced from environment variables."""

    slack_webhook_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_to: str = ""


class Notifier(ABC):
    """Abstract base class for pipeline result notifiers."""

    @abstractmethod
    def notify(self, result: PipelineResult) -> None:
        """
        Notify configured destinations with a summary of a completed PipelineResult.
        
        Parameters:
            result (PipelineResult): The completed pipeline result to summarize and deliver.
        
        Notes:
            Implementations must catch and log all exceptions and must not allow exceptions to propagate from `notify`.
        """
        pass


class ConsoleNotifier(Notifier):
    """Prints build summary to stdout.

    Always enabled and serves as the fallback notification channel.
    """

    def notify(self, result: PipelineResult) -> None:
        """
        Send the pipeline result summary to standard output.
        
        Prints the result's markdown summary to stdout. Exceptions raised while generating or printing the summary are caught and logged.
        
        Parameters:
            result (PipelineResult): Pipeline result whose markdown summary will be printed.
        """
        try:
            logger.info("Sending notification via console")
            summary = result.to_summary_md()
            print(summary)
        except Exception as e:
            logger.error(f"Console notifier failed: {e}")


class SlackNotifier(Notifier):
    """Posts build summary to Slack webhook URL.

    Uses stdlib urllib to send markdown-formatted message blocks.
    """

    def __init__(self, webhook_url: str) -> None:
        """
        Create a Slack notifier configured with the given incoming webhook URL.
        
        Parameters:
            webhook_url (str): Slack incoming webhook URL to which notifications will be posted.
        
        Raises:
            ValueError: If `webhook_url` is empty.
        """
        if not webhook_url:
            raise ValueError("Slack webhook URL is required")
        self.webhook_url = webhook_url

    def notify(self, result: PipelineResult) -> None:
        """
        Send the pipeline result summary to the configured Slack incoming webhook.
        
        Builds a Slack message containing the markdown summary from `result.to_summary_md()` and posts it to the notifier's webhook URL. All delivery errors (network, encoding, timeouts, and other exceptions) are caught and logged; this method does not raise.
        Parameters:
            result (PipelineResult): The pipeline result whose summary will be delivered to Slack.
        """
        try:
            logger.info("Sending notification via Slack")
            summary = result.to_summary_md()

            # Build Slack message payload with markdown blocks
            payload = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": summary,
                        },
                    }
                ]
            }

            # Encode payload as JSON
            json_data = json.dumps(payload).encode("utf-8")

            # Create POST request
            req = urllib.request.Request(
                self.webhook_url,
                data=json_data,
                headers={"Content-Type": "application/json"},
            )

            # Send request with 5-second timeout
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status != 200:
                    logger.error(
                        f"Slack webhook returned HTTP {response.status}"
                    )
                else:
                    logger.info("Slack notification sent successfully")

        except urllib.error.URLError as e:
            logger.error(f"Slack notification failed (network error): {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to encode Slack message payload: {e}")
        except TimeoutError:
            logger.error(f"Slack webhook connection timeout after 5 seconds")
        except Exception as e:
            logger.error(f"Unexpected error sending Slack notification: {e}")


class EmailNotifier(Notifier):
    """Sends build summary via email using SMTP.

    Supports TLS on port 587 (STARTTLS) and standard SMTP on port 25/465.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        email_to: str,
    ) -> None:
        """
        Initialize the EmailNotifier with SMTP connection and recipient settings.
        
        Parameters:
            smtp_host: SMTP server hostname.
            smtp_port: SMTP server port (commonly 587 for STARTTLS, 465 for SSL, 25 for plain).
            smtp_user: SMTP username to use for authentication (may be empty for anonymous).
            smtp_password: Password for smtp_user (may be empty if not required).
            email_to: Recipient email address or comma-separated list of addresses.
        
        Raises:
            ValueError: If `smtp_host` or `email_to` is missing.
        """
        if not all([smtp_host, email_to]):
            raise ValueError("SMTP_HOST and EMAIL_TO are required")
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.email_to = email_to

    def notify(self, result: PipelineResult) -> None:
        """
        Send the pipeline result summary to the configured SMTP recipients.
        
        Constructs a multipart plain-text email whose subject includes the CI job name and the overall status, and sends it via the configured SMTP host/port (10s timeout). Uses STARTTLS when the SMTP port is 587 and performs SMTP login when username and password are provided. Errors are caught and logged; the method does not raise exceptions.
        
        Parameters:
            result (PipelineResult): The pipeline result used to generate the markdown summary and to populate the email subject and body.
        """
        try:
            logger.info("Sending notification via email")
            summary = result.to_summary_md()

            # Create email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = (
                f"Build Notification: {result.ci_context.job_name} "
                f"— {result.overall.value.upper()}"
            )
            msg["From"] = self.smtp_user or f"noreply@{self.smtp_host}"
            msg["To"] = self.email_to

            # Attach markdown as plain text
            msg.attach(MIMEText(summary, "plain"))

            # Connect to SMTP server and send
            with smtplib.SMTP(
                self.smtp_host, self.smtp_port, timeout=10
            ) as server:
                # Use TLS if port is 587
                if self.smtp_port == 587:
                    server.starttls()

                # Authenticate if credentials provided
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)

                # Send message
                server.send_message(msg)
                logger.info("Email notification sent successfully")

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
        except smtplib.SMTPException as e:
            logger.error(f"SMTP protocol error: {e}")
        except TimeoutError:
            logger.error(
                f"SMTP connection timeout to {self.smtp_host}:{self.smtp_port}"
            )
        except OSError as e:
            logger.error(f"SMTP connection failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error sending email notification: {e}")


def create_notifiers_from_env() -> list[Notifier]:
    """
    Assemble enabled Notifier instances from environment variables.
    
    Reads environment variables to conditionally enable Slack and Email notifiers while always including a ConsoleNotifier. Enables SlackNotifier when MCT_SLACK_WEBHOOK_URL is set and has the expected Slack webhook prefix. Enables EmailNotifier when MCT_SMTP_HOST and MCT_EMAIL_TO are set; MCT_SMTP_PORT, MCT_SMTP_USER, and MCT_SMTP_PASSWORD are used if present. Misconfiguration or initialization errors are logged and cause the corresponding notifier to be skipped.
    
    Returns:
        list[Notifier]: Enabled notifiers; always includes a ConsoleNotifier.
    """
    notifiers: list[Notifier] = [ConsoleNotifier()]
    logger.info("Console notifier enabled (always-on)")

    # Check for Slack configuration
    slack_url = os.environ.get("MCT_SLACK_WEBHOOK_URL", "").strip()
    if slack_url:
        try:
            # Validate webhook URL format
            if not slack_url.startswith("https://hooks.slack.com/"):
                logger.warning(
                    f"Invalid Slack webhook URL format (should start with "
                    f"https://hooks.slack.com/); skipping Slack notifier"
                )
            else:
                notifiers.append(SlackNotifier(slack_url))
                logger.info("Slack notifier enabled")
        except ValueError as e:
            logger.warning(f"Slack notifier disabled: {e}")

    # Check for email configuration
    smtp_host = os.environ.get("MCT_SMTP_HOST", "").strip()
    email_to = os.environ.get("MCT_EMAIL_TO", "").strip()

    if smtp_host:
        if not email_to:
            logger.warning(
                "MCT_SMTP_HOST configured but MCT_EMAIL_TO not set; "
                "email notifier disabled"
            )
        else:
            try:
                smtp_port = int(os.environ.get("MCT_SMTP_PORT", "587"))
                smtp_user = os.environ.get("MCT_SMTP_USER", "").strip()
                smtp_password = os.environ.get("MCT_SMTP_PASSWORD", "").strip()

                notifiers.append(
                    EmailNotifier(
                        smtp_host=smtp_host,
                        smtp_port=smtp_port,
                        smtp_user=smtp_user,
                        smtp_password=smtp_password,
                        email_to=email_to,
                    )
                )
                logger.info("Email notifier enabled")
            except (ValueError, TypeError) as e:
                logger.warning(f"Email notifier disabled: {e}")

    return notifiers
