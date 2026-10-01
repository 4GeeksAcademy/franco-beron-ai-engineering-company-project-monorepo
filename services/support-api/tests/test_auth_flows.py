import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi import HTTPException

from app.main import change_password, forgot_password, reset_password
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.security import hash_password, verify_password


class FakeDocument(dict):
    def __init__(self, doc_id, **values):
        super().__init__(values)
        self.doc_id = doc_id


class PasswordResetTests(unittest.TestCase):
    def test_authenticated_password_change_replaces_hash(self):
        user = FakeDocument(
            4,
            password_hash=hash_password("current-password-value"),
        )
        payload = ChangePasswordRequest.model_construct(
            current_password="current-password-value",
            new_password="new-password-value",
        )

        with (
            patch("app.main.users.update") as update_user,
            patch("app.main.reset_tokens.search", return_value=[]),
        ):
            result = change_password(payload, user)

        new_hash = update_user.call_args.args[0]["password_hash"]
        self.assertTrue(verify_password("new-password-value", new_hash))
        self.assertIn("se actualizó", result["message"])

    def test_authenticated_password_change_requires_current_password(self):
        user = FakeDocument(
            4,
            password_hash=hash_password("current-password-value"),
        )
        payload = ChangePasswordRequest.model_construct(
            current_password="wrong-current-password",
            new_password="new-password-value",
        )

        with self.assertRaises(HTTPException):
            change_password(payload, user)

    def test_password_reset_updates_hash_and_consumes_token(self):
        user = FakeDocument(4, email="")
        reset_document = FakeDocument(
            9,
            user_id=user.doc_id,
            expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
            used=False,
        )

        with (
            patch("app.main.users.search", return_value=[user]),
            patch("app.main.users.get", return_value=user),
            patch("app.main.users.update") as update_user,
            patch(
                "app.main.reset_tokens.search",
                side_effect=[[], [reset_document], [reset_document], []],
            ),
            patch("app.main.reset_tokens.insert", return_value=reset_document.doc_id),
            patch("app.main.reset_tokens.update") as update_token,
            patch("app.main.send_password_reset_email") as send_email,
        ):
            forgot_result = forgot_password(
                ForgotPasswordRequest.model_construct(email="")
            )
            raw_token = send_email.call_args.kwargs["token"]
            reset_result = reset_password(
                ResetPasswordRequest.model_construct(
                    token=raw_token,
                    new_password="new-password-value",
                )
            )

            self.assertIn("Si la cuenta está registrada", forgot_result["message"])
            self.assertIn("se actualizó", reset_result["message"])
            password_hash = update_user.call_args.args[0]["password_hash"]
            self.assertTrue(verify_password("new-password-value", password_hash))
            update_token.assert_called_once_with(
                {"used": True},
                doc_ids=[reset_document.doc_id],
            )

            with self.assertRaises(HTTPException):
                reset_password(
                    ResetPasswordRequest.model_construct(
                        token=raw_token,
                        new_password="another-password-value",
                    )
                )

    def test_expired_reset_token_is_rejected(self):
        reset_document = FakeDocument(
            12,
            user_id=4,
            expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            used=False,
        )

        with (
            patch("app.main.reset_tokens.search", return_value=[reset_document]),
            patch("app.main.reset_tokens.update") as update_token,
        ):
            with self.assertRaises(HTTPException):
                reset_password(
                    ResetPasswordRequest.model_construct(
                        token="x" * 43,
                        new_password="new-password-value",
                    )
                )
            update_token.assert_called_once_with(
                {"used": True},
                doc_ids=[reset_document.doc_id],
            )


if __name__ == "__main__":
    unittest.main()