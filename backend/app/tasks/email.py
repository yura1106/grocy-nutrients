from app.tasks import celery


@celery.task(name="app.tasks.email.send_password_reset_email")
def send_password_reset_email_task(to_email: str, username: str, reset_token: str) -> bool:
    from app.services.email import send_password_reset_email

    return send_password_reset_email(to_email, username, reset_token)


@celery.task(name="app.tasks.email.send_account_deletion_email")
def send_account_deletion_email_task(to_email: str, username: str, deletion_token: str) -> bool:
    from app.services.email import send_account_deletion_email

    return send_account_deletion_email(to_email, username, deletion_token)


@celery.task(name="app.tasks.email.send_data_export_email")
def send_data_export_email_task(
    to_email: str, username: str, data: dict, export_type: str
) -> bool:
    from app.services.email import send_data_export_email

    return send_data_export_email(to_email, username, data, export_type)
