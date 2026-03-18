"""
Email notification service for the video transcoding pipeline.

Sends emails when:
- Video upload completes validation (approved/rejected)
- Transcoding job completes (success/failure)
- All transcoding jobs for a video finish

Supports SendGrid (production) and SMTP (development/fallback).
Falls back to console logging if no email provider is configured.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from app.metrics import emails_sent_total


# ─────────────────────────────────────────────────────────────────
# EMAIL PROVIDER DETECTION
# ─────────────────────────────────────────────────────────────────

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@videotranscoder.local")
APP_NAME = "Video Transcoding Pipeline"


def _get_provider() -> str:
    """
    Detect which email provider to use.
    
    Priority:
    1. SendGrid (if API key is set) — best for production
    2. SMTP (if host is set) — works with Gmail, Outlook, etc.
    3. Console (fallback) — just prints to Docker logs
    """
    if SENDGRID_API_KEY:
        return "sendgrid"
    if SMTP_HOST and SMTP_USER:
        return "smtp"
    return "console"


# ─────────────────────────────────────────────────────────────────
# SEND FUNCTIONS (one per provider)
# ─────────────────────────────────────────────────────────────────

def _send_via_sendgrid(to_email: str, subject: str, html_body: str) -> bool:
    """Send email using SendGrid API."""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email=FROM_EMAIL,
            to_emails=to_email,
            subject=subject,
            html_content=html_body
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        return response.status_code in (200, 201, 202)
    except Exception as e:
        print(f"❌ SendGrid error: {e}")
        return False


def _send_via_smtp(to_email: str, subject: str, html_body: str) -> bool:
    """Send email using SMTP (Gmail, Outlook, etc.)."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = FROM_EMAIL
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ SMTP error: {e}")
        return False


def _send_via_console(to_email: str, subject: str, html_body: str) -> bool:
    """
    Fallback: log email to console (development mode).
    
    This lets you see exactly what emails WOULD be sent
    without configuring any email provider.
    """
    print(f"\n{'='*60}")
    print(f"📧 EMAIL NOTIFICATION (console mode)")
    print(f"{'='*60}")
    print(f"  To:      {to_email}")
    print(f"  Subject: {subject}")
    print(f"  Time:    {datetime.utcnow().isoformat()}")
    print(f"{'='*60}\n")
    return True


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Send an email using the best available provider.
    Records success/failure in Prometheus metrics.
    
    This is the main function — all notification functions below use this.
    """
    provider = _get_provider()

    if provider == "sendgrid":
        success = _send_via_sendgrid(to_email, subject, html_body)
    elif provider == "smtp":
        success = _send_via_smtp(to_email, subject, html_body)
    else:
        success = _send_via_console(to_email, subject, html_body)

    # Record in Prometheus (this feeds the "Emails sent" Grafana panel)
    emails_sent_total.labels(type="success" if success else "failure").inc()
    return success


# ─────────────────────────────────────────────────────────────────
# HTML EMAIL TEMPLATE
# ─────────────────────────────────────────────────────────────────

def _base_template(title: str, content: str) -> str:
    """
    Wrap content in a styled email template.
    
    Every email looks professional with a branded header,
    clean typography, and a footer with timestamp.
    """
    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 24px; border-radius: 12px 12px 0 0; text-align: center;">
            <h1 style="color: white; margin: 0; font-size: 22px;">
                {APP_NAME}
            </h1>
        </div>
        <div style="background: #ffffff; padding: 24px; border: 1px solid #e2e8f0;
                    border-top: none; border-radius: 0 0 12px 12px;">
            <h2 style="color: #1a202c; margin-top: 0;">{title}</h2>
            {content}
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;">
            <p style="color: #718096; font-size: 12px; text-align: center;">
                Sent by {APP_NAME} at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
            </p>
        </div>
    </div>
    """


# ─────────────────────────────────────────────────────────────────
# NOTIFICATION FUNCTIONS (called from workers/API)
# ─────────────────────────────────────────────────────────────────

def notify_upload_approved(to_email: str, filename: str, video_id: int,
                           resolution: str, qualities: list):
    """
    Notify user their video passed validation and is queued for transcoding.
    Called from: videos.py after inspection passes.
    """
    quality_list = ", ".join(qualities)
    content = f"""
    <p style="color: #2d3748;">Your video has passed all quality checks and is now
    being transcoded.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
        <tr style="background: #f7fafc;">
            <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: 600;">Filename</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;">{filename}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: 600;">Video ID</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;">#{video_id}</td>
        </tr>
        <tr style="background: #f7fafc;">
            <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: 600;">Resolution</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;">{resolution}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: 600;">Transcoding to</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;">{quality_list}</td>
        </tr>
    </table>
    <p style="color: #38a169; font-weight: 600;">
        Transcoding is in progress. You'll receive another email when it's done.
    </p>
    """
    html = _base_template("Video Approved", content)
    return send_email(to_email, f"[{APP_NAME}] Video approved: {filename}", html)


def notify_upload_rejected(to_email: str, filename: str, reason: str):
    """
    Notify user their video failed validation.
    Called from: videos.py after inspection fails.
    """
    content = f"""
    <p style="color: #2d3748;">Unfortunately, your video did not pass our quality checks.</p>
    <div style="background: #fff5f5; border-left: 4px solid #fc8181; padding: 12px 16px;
                margin: 16px 0; border-radius: 0 8px 8px 0;">
        <p style="color: #c53030; font-weight: 600; margin: 0 0 4px 0;">Rejection reason:</p>
        <p style="color: #742a2a; margin: 0;">{reason}</p>
    </div>
    <p style="color: #2d3748;"><strong>Filename:</strong> {filename}</p>
    <p style="color: #718096;">Please fix the issues above and try uploading again.</p>
    """
    html = _base_template("Video Rejected", content)
    return send_email(to_email, f"[{APP_NAME}] Video rejected: {filename}", html)


def notify_transcoding_complete(to_email: str, filename: str, video_id: int,
                                 transcoded_versions: list, total_time: float):
    """
    Notify user all transcoding jobs finished successfully.
    Called from: chunked_transcoder.py after final quality finishes.
    """
    rows = ""
    for v in transcoded_versions:
        status_icon = "&#10004;" if v.get("verification_passed") else "&#9888;"
        status_color = "#38a169" if v.get("verification_passed") else "#d69e2e"
        rows += f"""
        <tr>
            <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: 600;">
                {v['quality']}
            </td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;">
                {v.get('file_size_mb', 0)} MB
            </td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;">
                {v.get('similarity_score', 0)}%
            </td>
            <td style="padding: 10px; border: 1px solid #e2e8f0; text-align: center;">
                <span style="color: {status_color}; font-size: 18px;">{status_icon}</span>
            </td>
        </tr>
        """

    content = f"""
    <p style="color: #2d3748;">All transcoding jobs for your video are complete.</p>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
        <tr style="background: #edf2f7;">
            <th style="padding: 10px; border: 1px solid #e2e8f0; text-align: left;">Quality</th>
            <th style="padding: 10px; border: 1px solid #e2e8f0; text-align: left;">Size</th>
            <th style="padding: 10px; border: 1px solid #e2e8f0; text-align: left;">Similarity</th>
            <th style="padding: 10px; border: 1px solid #e2e8f0; text-align: center;">Verified</th>
        </tr>
        {rows}
    </table>
    <p style="color: #718096;">
        <strong>Total processing time:</strong> {total_time:.1f} seconds<br>
        <strong>Video ID:</strong> #{video_id}
    </p>
    <p style="color: #2d3748;">
        You can download your transcoded videos from the dashboard.
    </p>
    """
    html = _base_template("Transcoding Complete", content)
    return send_email(to_email, f"[{APP_NAME}] Transcoding complete: {filename}", html)


def notify_transcoding_failed(to_email: str, filename: str, video_id: int,
                               quality: str, error: str):
    """
    Notify user a transcoding job failed.
    Called from: chunked_transcoder.py in the except block.
    """
    content = f"""
    <p style="color: #2d3748;">A transcoding job encountered an error.</p>
    <div style="background: #fff5f5; border-left: 4px solid #fc8181; padding: 12px 16px;
                margin: 16px 0; border-radius: 0 8px 8px 0;">
        <p style="color: #c53030; font-weight: 600; margin: 0 0 4px 0;">Error details:</p>
        <p style="color: #742a2a; margin: 0;">{error}</p>
    </div>
    <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
        <tr style="background: #f7fafc;">
            <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: 600;">Video</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;">{filename} (ID: #{video_id})</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #e2e8f0; font-weight: 600;">Quality</td>
            <td style="padding: 10px; border: 1px solid #e2e8f0;">{quality}</td>
        </tr>
    </table>
    <p style="color: #718096;">The system will retry the job automatically.
    If the issue persists, please contact support.</p>
    """
    html = _base_template("Transcoding Failed", content)
    return send_email(to_email, f"[{APP_NAME}] Transcoding failed: {filename}", html)