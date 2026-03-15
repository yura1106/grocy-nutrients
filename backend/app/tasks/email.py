from app.tasks import celery


@celery.task(name="app.tasks.email.send_password_reset_email")
def send_password_reset_email_task(to_email: str, username: str, reset_token: str) -> bool:
    from app.services.email import send_password_reset_email

    return send_password_reset_email(to_email, username, reset_token)
