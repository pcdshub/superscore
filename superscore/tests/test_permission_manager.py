from unittest.mock import MagicMock

import pytest

from superscore.permission_manager import PermissionManager


class TestPermissionManager:

    def setup_method(self) -> None:
        """Reset the singleton before each test and set up signal handling"""
        PermissionManager._instance = None
        self.manager = PermissionManager.get_instance()

        self.signal_received = False
        self.signal_value = None

        self.manager.admin_status_changed.connect(self.on_admin_status_changed)

    def teardown_method(self) -> None:
        """Clean up signal connections after each test"""
        if hasattr(self, 'manager'):
            self.manager.admin_status_changed.disconnect(self.on_admin_status_changed)

    def on_admin_status_changed(self, value) -> None:
        """Signal handler for admin status changes"""
        self.signal_received = True
        self.signal_value = value

    def test_get_instance(self) -> None:
        """Test that get_instance returns a singleton instance"""
        instance1 = PermissionManager.get_instance()
        instance2 = PermissionManager.get_instance()

        assert instance1 is instance2
        assert isinstance(instance1, PermissionManager)

    def test_init_singleton_enforcement(self) -> None:
        """Test that direct instantiation raises an exception after singleton is created"""
        PermissionManager.get_instance()

        with pytest.raises(Exception) as excinfo:
            PermissionManager()

        assert "This class is a singleton" in str(excinfo.value)

    def test_admin_login_with_correct_credentials(self) -> None:
        """Test admin login with correct credentials"""
        self.signal_received = False
        self.signal_value = None

        result = self.manager.admin_login("admin@example.com", "password")

        assert result
        assert self.manager.is_admin()
        assert self.manager.get_admin_token() == "dummy_token"
        assert self.signal_received
        assert self.signal_value

    def test_admin_login_with_incorrect_credentials(self) -> None:
        """Test admin login with incorrect credentials"""
        self.signal_received = False

        result = self.manager.admin_login("wrong@example.com", "wrong_password")

        assert not result
        assert not self.manager.is_admin()
        assert self.manager.get_admin_token() is None
        assert not self.signal_received

    def test_admin_login_with_backend_api(self) -> None:
        """Test admin login with backend API"""
        mock_api: MagicMock = MagicMock()
        mock_api.admin_login.return_value = {"success": True, "token": "api_token"}

        self.signal_received = False

        result = self.manager.admin_login("admin@example.com", "password", backend_api=mock_api)

        assert result
        assert self.manager.is_admin()
        assert self.manager.get_admin_token() == "api_token"
        assert self.signal_received
        mock_api.admin_login.assert_called_once_with("admin@example.com", "password")

    def test_admin_logout(self) -> None:
        """Test admin logout"""
        self.manager.admin_login("admin@example.com", "password")

        self.signal_received = False
        self.signal_value = None

        self.manager.admin_logout()

        assert not self.manager.is_admin()
        assert self.manager.get_admin_token() is None
        assert self.signal_received

    def test_is_admin(self) -> None:
        """Test is_admin method"""
        assert not self.manager.is_admin()

        self.manager.admin_login("admin@example.com", "password")
        assert self.manager.is_admin()

        self.manager.admin_logout()
        assert not self.manager.is_admin()

    def test_get_admin_token(self) -> None:
        """Test get_admin_token method"""
        assert self.manager.get_admin_token() is None

        self.manager.admin_login("admin@example.com", "password")
        assert self.manager.get_admin_token() == "dummy_token"

        self.manager.admin_logout()
        assert self.manager.get_admin_token() is None
