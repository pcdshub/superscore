from qtpy.QtCore import Signal, QObject

class PermissionManager(QObject):
    admin_status_changed = Signal(bool)
    
    _instance = None
    
    @staticmethod
    def get_instance():
        """Get or create the singleton instance"""
        if PermissionManager._instance is None:
            PermissionManager._instance = PermissionManager()
        return PermissionManager._instance
    
    def __init__(self):
        """Initialize the permission manager"""
        super().__init__()
        if PermissionManager._instance is not None:
            raise Exception("This class is a singleton. Use get_instance() instead.")
        else:
            PermissionManager._instance = self
            
        self._admin_token = None
        self._is_admin = False
    
    def admin_login(self, email, password, backend_api=None):
        """Authenticate as admin"""
        # Call backend API to authenticate admin
        # For this example, we'll use a simple check
        # replace with backend authentication
        if backend_api:
            result = backend_api.admin_login(email, password)
            success = result.get("success", False)
            if success:
                self._admin_token = result.get("token", "dummy_token")
        else:
            # Simple local authentication for testing
            success = (email == "admin@example.com" and password == "password")
            if success:
                self._admin_token = "dummy_token"
        
        if success:
            self._is_admin = True
            self.admin_status_changed.emit(True)
            
        return success
    
    def admin_logout(self):
        """Log out from admin mode"""
        if self._is_admin:
            self._admin_token = None
            self._is_admin = False
            
            self.admin_status_changed.emit(False)
    
    def is_admin(self):
        """Check if currently in admin mode"""
        return self._is_admin
    
    def get_admin_token(self):
        """Get current admin token (for backend calls)"""
        if self.is_admin():
            return self._admin_token
        return None