import os
import resend
import threading

def _allowed_filename(filename: str) -> bool:
    ALLOWED_EXTENSIONS = {".csv"}
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXTENSIONS

def _get_env_or_docker_default(key, default=None):
    """
    Get environment variable, or fall back to docker-compose.yml default if available.
    """
    val = os.environ.get(key)
    if val:
        return val

    try:
        docker_compose_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docker-compose.yml')
        if os.path.exists(docker_compose_path):
            with open(docker_compose_path, 'r') as f:
                content = f.read()
                import re
                match = re.search(fr"{key}=\${{{key}:-(.*?)}}", content)
                if match:
                    return match.group(1)
    except Exception:
        pass

    return default

def send_email_notification(subject, body):
    api_key = _get_env_or_docker_default("RESEND_API_KEY")
    if not api_key:
        print("⚠️  Resend API Key missing. Skipping email.", flush=True)
        return

    resend.api_key = api_key
    recipients = ["shriram2222@gmail.com"]

    print(f"📧 Sending email via Resend to {recipients}...", flush=True)

    try:
        params = {
            "from": "Trade Auditor <onboarding@resend.dev>",
            "to": recipients,
            "subject": subject,
            "text": body,
        }

        email = resend.Emails.send(params)
        print(f"✅ Email sent successfully! ID: {email.get('id')}", flush=True)
    except Exception as e:
        print(f"❌ Failed to send email: {e}", flush=True)
