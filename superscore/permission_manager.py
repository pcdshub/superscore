from typing import Optional

from qtpy.QtCore import QObject, Signal


class PermissionManager(QObject):
    """
    Permission manager singleton class for handling admin authentication.

    This class manages admin authentication state and provides methods to login,
    logout, and check admin status. It follows the singleton pattern to ensure
    only one instance exists throughout the application.

    Attributes
    ----------
    admin_status_changed : Signal
        Signal emitted when admin status changes, with boolean parameter indicating new status
    _instance : PermissionManager or None
        Class variable holding the singleton instance
    """
    admin_status_changed = Signal(bool)
    _instance = None

    @staticmethod
    def get_instance() -> None:
        """
        Get or create the singleton instance.

        Returns
        -------
        PermissionManager
            The singleton instance of PermissionManager
        """
        if PermissionManager._instance is None:
            PermissionManager._instance = PermissionManager()
        return PermissionManager._instance

    def __init__(self) -> None:
        """
        Initialize the permission manager.

        Creates a new PermissionManager instance if none exists yet. Raises an exception
        if an instance already exists, enforcing the singleton pattern.

        Raises
        ------
        Exception
            If attempting to create a second instance
        """
        super().__init__()
        if PermissionManager._instance is not None:
            raise Exception("This class is a singleton. Use get_instance() instead.")
        else:
            PermissionManager._instance = self
        self._admin_token = None
        self._is_admin = False

    def admin_login(self, email, password, backend_api=None) -> bool:
        """
        Authenticate as admin.

        Attempts to authenticate using the provided credentials. If a backend API is provided,
        it will use that for authentication.

        Otherwise, it uses a simple local authentication
        mechanism for testing purposes. (#TODO This should be replaced with a real API call in production.)

        Parameters
        ----------
        email : str
            Admin email address
        password : str
            Admin password
        backend_api : object, optional
            Backend API object with admin_login method, by default None

        Returns
        -------
        bool
            True if authentication was successful, False otherwise

        Notes
        -----
        When authentication is successful, the admin_status_changed signal is emitted
        with value True.
        """
        success: bool = False

        if backend_api:
            result = backend_api.admin_login(email, password)
            success = result.get("success", False)
            if success:
                self._admin_token = result.get("token", "dummy_token")
        else:
            success = (email == "admin@example.com" and password == "password")
            if success:
                self._admin_token = "dummy_token"

        if success:
            self._is_admin = True
            self.admin_status_changed.emit(True)

        return success

    def admin_logout(self) -> None:
        """
        Log out from admin mode.

        Clears admin token and status if currently logged in as admin.
        Emits the admin_status_changed signal with False when logout occurs.

        Returns
        -------
        None
        """
        if self._is_admin:
            self._admin_token = None
            self._is_admin = False
            self.admin_status_changed.emit(False)

    def is_admin(self) -> bool:
        """
        Check if currently in admin mode.

        Returns
        -------
        bool
            True if currently authenticated as admin, False otherwise
        """
        return self._is_admin

    def get_admin_token(self) -> Optional[str]:
        """
        Get current admin token for backend calls.

        Returns
        -------
        str or None
            The admin authentication token if authenticated as admin, None otherwise
        """
        if self.is_admin():
            return self._admin_token
        return None

    def set_admin_mode(self, enabled: bool = True) -> None:
        """
        Directly set admin mode.

        Parameters
        ----------
        enabled : bool, optional
            Whether to enable admin mode, by default True
        """
        if enabled and not self._is_admin:
            self._admin_token = "launch_flag_token"
            self._is_admin = True
            self.admin_status_changed.emit(True)
        elif not enabled and self._is_admin:
            self.admin_logout()
