"""Client notification emails must use absolute links when APP_BASE_URL is set."""

from unittest.mock import patch

from app.services.client_notification_service import ClientNotificationService


def test_absolutize_link_joins_base_url(app):
    with app.app_context():
        app.config["APP_BASE_URL"] = "https://time.example.com"
        svc = ClientNotificationService()
        assert (
            svc._absolutize_link("/client-portal/invoices/42")
            == "https://time.example.com/client-portal/invoices/42"
        )


def test_absolutize_link_preserves_absolute(app):
    with app.app_context():
        app.config["APP_BASE_URL"] = "https://time.example.com"
        svc = ClientNotificationService()
        assert svc._absolutize_link("https://other.example/path") == "https://other.example/path"


def test_send_email_notification_passes_absolute_link(app):
    with app.app_context():
        app.config["APP_BASE_URL"] = "https://time.example.com"
        notification = type(
            "N",
            (),
            {
                "client_id": 1,
                "type": "invoice_created",
                "title": "New Invoice",
                "message": "Hi",
                "link_url": "/client-portal/invoices/7",
                "link_text": "View",
            },
        )()
        prefs = type(
            "P",
            (),
            {"email_enabled": True, "should_send_email": lambda self, t: True},
        )()
        contact = type("C", (), {"email": "c@example.com", "is_active": True})()

        with (
            patch(
                "app.services.client_notification_service.ClientNotificationPreferences.query"
            ) as prefs_q,
            patch("app.services.client_notification_service.Contact.query") as contact_q,
            patch("app.services.client_notification_service.send_template_email") as mock_send,
        ):
            prefs_q.filter_by.return_value.first.return_value = prefs
            contact_q.filter_by.return_value.all.return_value = [contact]
            ClientNotificationService()._send_email_notification(notification)
            assert mock_send.called
            assert (
                mock_send.call_args.kwargs["absolute_link_url"]
                == "https://time.example.com/client-portal/invoices/7"
            )
