from qtpy.QtWidgets import (QFrame, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                           QWidget, QStackedWidget, QMessageBox)
from qtpy.QtCore import Qt, QSize
from qtpy.QtGui import QIcon, QPixmap
import qtawesome as qta

from superscore.permission_manager import PermissionManager


class AdminPage(QWidget):
    def __init__(self, backend_api=None):
        super().__init__()

        self.backend_api = backend_api
        
        self.permission_manager = PermissionManager.get_instance()
        self.permission_manager.admin_status_changed.connect(self.on_admin_status_changed)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        header = self.create_header()
        main_layout.addWidget(header)
        
        self.content_area = QStackedWidget()
        self.content_area.setObjectName("contentArea")
        
        login_page = self.create_login_page()
        self.content_area.addWidget(login_page)
        
        main_page = self.create_main_page()
        self.content_area.addWidget(main_page)
        
        self.content_area.setCurrentIndex(0)
        
        main_layout.addWidget(self.content_area)
    
    def create_header(self):
        """Create application header with logo"""
        header = QFrame()
        header.setObjectName("appHeader")
        header.setFixedHeight(80)
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 0, 20, 0)
        
        icon_label = QLabel()
        icon_pixmap = QPixmap("assets/Squirrel_Icon.png")
        icon_pixmap = icon_pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(icon_pixmap)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        
        app_name = QLabel("<b>Squirrel</b><br>Admin Log In</br>")
        app_name.setObjectName("appNameLabel")
        
        text_layout.addWidget(app_name)
        
        layout.addWidget(icon_label)
        layout.addLayout(text_layout)
        layout.addStretch()
        
        return header
    
    def create_login_page(self):
        """Create the login page with centered login frame"""
        login_page = QWidget()
        login_page.setObjectName("loginPage")
        
        layout = QVBoxLayout(login_page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        layout.addStretch(1)
        
        h_layout = QHBoxLayout()
        h_layout.addStretch(1)
        
        login_frame = self.create_login_frame()
        h_layout.addWidget(login_frame)
        h_layout.addStretch(1)
        
        layout.addLayout(h_layout)
        
        layout.addStretch(1)
        
        return login_page
    
    def create_login_frame(self):
        """Create the login form frame"""
        login_frame = QFrame()
        login_frame.setObjectName("loginFrame")
        login_frame.setFixedSize(450, 300)
        login_frame.setFrameShape(QFrame.StyledPanel)
        
        layout = QVBoxLayout(login_frame)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        header_layout = QHBoxLayout()
        
        title = QLabel("<big>Admin Log in</big> <br>Please enter your details</br>")
        title.setObjectName("loginTitle")
        
        header_layout.addWidget(title)
        
        self.email_field = QLineEdit()
        self.email_field.setPlaceholderText("Email")
        self.email_field.setObjectName("emailField")
        
        self.password_field = QLineEdit()
        self.password_field.setPlaceholderText("Password")
        self.password_field.setEchoMode(QLineEdit.Password)
        self.password_field.setObjectName("passwordField")
        
        login_button = QPushButton("Log in")
        login_button.setObjectName("loginButton")
        login_button.clicked.connect(self.try_login)
        
        layout.addLayout(header_layout)
        layout.addSpacing(10)
        layout.addWidget(self.email_field)
        layout.addWidget(self.password_field)
        layout.addSpacing(20)
        layout.addWidget(login_button)
        
        self.email_field.returnPressed.connect(self.password_field.setFocus)
        self.password_field.returnPressed.connect(self.try_login)
        
        return login_frame
    
    def create_main_page(self):
        """Create the main application page (shown after login)"""
        main_page = QWidget()
        main_page.setObjectName("mainPage")
        
        layout = QVBoxLayout(main_page)
        
        welcome_label = QLabel("Welcome to Admin Dashboard")
        welcome_label.setObjectName("welcomeLabel")
        welcome_label.setAlignment(Qt.AlignCenter)
        
        logout_button = QPushButton("Logout")
        logout_button.clicked.connect(self.logout)
        
        layout.addStretch(1)
        layout.addWidget(welcome_label)
        layout.addSpacing(20)
        layout.addWidget(logout_button, 0, Qt.AlignCenter)
        layout.addStretch(1)
        
        return main_page
    
    def try_login(self):
        """Process login attempt using PermissionManager"""
        email = self.email_field.text()
        password = self.password_field.text()
        
        if not email or not password:
            QMessageBox.warning(self, "Login Error", "Please enter both email and password")
            return
        
        if self.permission_manager.admin_login(email, password, self.backend_api):
            pass
        else:
            QMessageBox.warning(self, "Login Failed", "Invalid email or password")
            self.password_field.clear()
            self.password_field.setFocus()
    
    def logout(self):
        """Log out using PermissionManager"""
        self.permission_manager.admin_logout()
    
    def on_admin_status_changed(self, is_admin):
        """Handle admin status changes"""
        if is_admin:
            self.content_area.setCurrentIndex(1)
            self.password_field.clear()
        else:
            self.content_area.setCurrentIndex(0)
            self.email_field.clear()
            self.email_field.setFocus()
    

