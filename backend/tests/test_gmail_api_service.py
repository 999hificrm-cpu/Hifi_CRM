import pytest
from unittest.mock import patch, MagicMock
from app.services.gmail_service import (
    validate_send_as_identity,
    send_email_via_gmail,
    is_gmail_configured
)

def test_is_gmail_configured():
    with patch("app.services.gmail_service.settings") as mock_settings:
        mock_settings.GOOGLE_CLIENT_ID = "client_id"
        mock_settings.GOOGLE_CLIENT_SECRET = "client_secret"
        assert is_gmail_configured() is True
        
        mock_settings.GOOGLE_CLIENT_ID = None
        assert is_gmail_configured() is False


@patch("app.services.gmail_service.list_send_as_identities")
def test_validate_send_as_identity_primary(mock_list):
    # Primary identity should always be valid
    mock_list.return_value = [
        {"sendAsEmail": "lokeshsohanda10@gmail.com", "isPrimary": True, "verificationStatus": "accepted"},
        {"sendAsEmail": "admin@apex.com", "isPrimary": False, "verificationStatus": "pending"}
    ]
    
    result = validate_send_as_identity("fake_token", "lokeshsohanda10@gmail.com")
    assert result["sendAsEmail"] == "lokeshsohanda10@gmail.com"
    assert result["isPrimary"] is True


@patch("app.services.gmail_service.list_send_as_identities")
def test_validate_send_as_identity_verified_alias(mock_list):
    # Verified alias should be valid
    mock_list.return_value = [
        {"sendAsEmail": "lokeshsohanda10@gmail.com", "isPrimary": True, "verificationStatus": "accepted"},
        {"sendAsEmail": "admin@apex.com", "isPrimary": False, "verificationStatus": "accepted"}
    ]
    
    result = validate_send_as_identity("fake_token", "admin@apex.com")
    assert result["sendAsEmail"] == "admin@apex.com"


@patch("app.services.gmail_service.list_send_as_identities")
def test_validate_send_as_identity_unverified_alias(mock_list):
    # Unverified alias should raise ValueError
    mock_list.return_value = [
        {"sendAsEmail": "lokeshsohanda10@gmail.com", "isPrimary": True, "verificationStatus": "accepted"},
        {"sendAsEmail": "admin@apex.com", "isPrimary": False, "verificationStatus": "pending"}
    ]
    
    with pytest.raises(ValueError, match="not verified"):
        validate_send_as_identity("fake_token", "admin@apex.com")


@patch("app.services.gmail_service.list_send_as_identities")
def test_validate_send_as_identity_not_found(mock_list):
    # Identity not in list should raise ValueError
    mock_list.return_value = [
        {"sendAsEmail": "lokeshsohanda10@gmail.com", "isPrimary": True, "verificationStatus": "accepted"}
    ]
    
    with pytest.raises(ValueError, match="not a configured Send-As identity"):
        validate_send_as_identity("fake_token", "admin@apex.com")


@patch("app.services.gmail_service.validate_send_as_identity")
@patch("app.services.gmail_service.httpx.Client")
def test_send_email_via_gmail_success(mock_client, mock_validate):
    # Mock validation success
    mock_validate.return_value = {
        "sendAsEmail": "admin@apex.com",
        "displayName": "Apex Admin"
    }
    
    # Mock httpx response
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"id": "msg123", "threadId": "thread123"}
    
    mock_instance = mock_client.return_value.__enter__.return_value
    mock_instance.post.return_value = mock_resp
    
    result = send_email_via_gmail(
        access_token="fake_token",
        from_email="admin@apex.com",
        from_name="Apex Admin",
        to_email="lead@example.com",
        subject="Test Subject",
        body="Test Body"
    )
    
    assert result["success"] is True
    assert result["gmail_message_id"] == "msg123"
    assert result["from_email"] == "admin@apex.com"
    
    # Ensure correct API endpoint was called
    mock_instance.post.assert_called_once()
    args, kwargs = mock_instance.post.call_args
    assert "messages/send" in args[0]
    assert "json" in kwargs
    assert "raw" in kwargs["json"]
