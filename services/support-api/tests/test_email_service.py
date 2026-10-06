import unittest
from unittest.mock import patch

from app.email_service import send_password_reset_email


class EmailServiceTests(unittest.TestCase):
    def test_reset_email_uses_configured_frontend_and_sender(self):
        with (
            patch("app.email_service.RESEND_API_KEY", "test-only-key"),
            patch("app.email_service.EMAIL_FROM", "Nexova Ops"),
            patch("app.email_service.FRONTEND_URL", "http://localhost:4174"),
            patch("app.email_service.resend.Emails.send") as send_email,
        ):
            send_password_reset_email(to_email="", token="reset-token-value")

        message = send_email.call_args.args[0]
        self.assertEqual(message["from"], "Nexova Ops")
        self.assertEqual(message["to"], [""])
        self.assertIn(
            "http://localhost:4174/?reset_token=reset-token-value",
            message["html"],
        )

    def test_missing_resend_key_fails_without_network_call(self):
        with (
            patch("app.email_service.RESEND_API_KEY", ""),
            patch("app.email_service.resend.Emails.send") as send_email,
            self.assertRaises(RuntimeError),
        ):
            send_password_reset_email(to_email="", token="reset-token-value")
        send_email.assert_not_called()


if __name__ == "__main__":
    unittest.main()