
import aqt
import aqt.utils
import anki

import json
import requests

from aqt.qt import *
from aqt import mw

def get_local_deck_from_hash(input_hash):
    strings_data = mw.addonManager.getConfig(__name__)
    if strings_data:
        for hash, details in strings_data.items():
            if hash == input_hash:
                return mw.col.decks.name(details["deckId"])
    return "None"

def store_login_token(token):
    strings_data = mw.addonManager.getConfig(__name__)
    if strings_data:
        if "settings" not in strings_data:
            strings_data["settings"] = {}
        strings_data["settings"]["token"] = token
        strings_data["settings"]["auto_approve"] = False
    mw.addonManager.writeConfig(__name__, strings_data)

def get_login_token():
    strings_data = mw.addonManager.getConfig(__name__)
    if strings_data:
        if "settings" in strings_data:
            if "token" in strings_data["settings"]:
                return strings_data["settings"]["token"]
    return None   

class ChangelogDialog(QDialog):
    def __init__(self, changelog, deck_hash):
        super().__init__()
        local_name = get_local_deck_from_hash(deck_hash)
        self.setWindowTitle(f"AnkiCollab - Changelog for Deck {local_name}")
        self.setModal(True)

        layout = QVBoxLayout()

        label = QLabel("The following changes are available:")
        layout.addWidget(label)

        changelog_text = QTextBrowser()
        
        if not changelog:
            changelog = "The maintainer left no changelog message for this update."
            
        changelog_text.setPlainText(changelog)
        layout.addWidget(changelog_text)

        button_box = QDialogButtonBox()
        install_button = button_box.addButton("Install Now", QDialogButtonBox.ButtonRole.AcceptRole)
        later_button = button_box.addButton("Decide Later", QDialogButtonBox.ButtonRole.RejectRole)
        skip_button = QPushButton("Skip this Update")
        button_box.addButton(skip_button, QDialogButtonBox.ButtonRole.ActionRole)

        layout.addWidget(button_box)

        self.setLayout(layout)

        install_button.clicked.connect(self.accept)
        later_button.clicked.connect(self.reject)
        skip_button.clicked.connect(self.skip_update)

        self.adjustSize()

    def skip_update(self):
        self.done(2)
        

class OptionalTagsDialog(QDialog):
    checkboxes = {}
    
    def __init__(self, old_tags, new_tags):
        super().__init__()
        layout = QVBoxLayout()

        self.setWindowTitle("AnkiCollab - Optional Tags")
        label = QLabel("You can subscribe to the following optional tags:")
        layout.addWidget(label)
        
        for item in new_tags:
            checkbox = QCheckBox(item)
            #set checked to the old value if it exists in the old tags, otherwise set it to false
            checkbox.setChecked(old_tags.get(item, False))
            self.checkboxes[item] = checkbox
            layout.addWidget(checkbox)

        button = QPushButton('Save')
        button.clicked.connect(lambda: self.close())
        layout.addWidget(button)

        self.setLayout(layout)
        self.show()

    def get_selected_tags(self):
        result = {}
        for item in self.checkboxes:
            result[item] = self.checkboxes[item].isChecked()

        return result
    
    
# Create a new Login Dialog that allows the user to enter their username and password
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super(LoginDialog, self).__init__(parent)
        self.setWindowTitle("AnkiCollab - Login")
        self.setModal(True)
        self.resize(300, 100)

        layout = QVBoxLayout()

        label = QLabel("Please enter your AnkiCollab email and password:")
        layout.addWidget(label)

        form_layout = QFormLayout()

        self.email_input = QLineEdit()
        form_layout.addRow("Email:", self.email_input)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("Password:", self.password_input)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox()
        login_button = button_box.addButton("Login", QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)

        layout.addWidget(button_box)

        self.setLayout(layout)

        login_button.clicked.connect(self.login)

    def login(self):
        email = self.email_input.text()
        password = self.password_input.text()
        if not email or not password:
            aqt.mw.taskman.run_on_main(lambda: aqt.utils.showInfo("Please enter a email and password."))
            return
        
        payload = {
            'email': email,
            'password': password
        }
        response = requests.post("https://plugin.ankicollab.com/login", data=payload)

        if response.status_code == 200:
            res = response.text
            msg_box = QMessageBox()
            # if res is exactly 32 characters and no spaces, it's a token and we can assume it's a success
            if len(res) == 32 and " " not in res:
                store_login_token(res)
                msg_box.setText("Login successful!")
                self.done(0)
            else:
                msg_box.setText(res)
            msg_box.exec()
        else:
            aqt.mw.taskman.run_on_main(lambda: aqt.utils.showInfo("An error occurred while logging in. Please try again."))
            return
  
class AddChangelogDialog(QDialog):
    def __init__(self, deck_hash, parent=None):
        super().__init__()
        self.setWindowTitle("AnkiCollab - Add Changelog")
        self.setModal(True)
        self.resize(400, 200)

        self.deck_hash = deck_hash

        layout = QVBoxLayout()

        label = QLabel("Please enter the changelog message:")
        layout.addWidget(label)

        self.changelog_input = QTextEdit()
        layout.addWidget(self.changelog_input)

        button_box = QDialogButtonBox()
        publish_button = button_box.addButton("Publish", QDialogButtonBox.ButtonRole.AcceptRole)
        button_box.addButton("Cancel", QDialogButtonBox.ButtonRole.RejectRole)

        layout.addWidget(button_box)

        self.setLayout(layout)

        publish_button.clicked.connect(self.publish)

    def publish(self):
        changelog_text = self.changelog_input.toPlainText()
        if not changelog_text:
            QMessageBox.warning(self, "Error", "Please enter a changelog message.")
            return

        payload = {
            'deck_hash': self.deck_hash,
            'changelog': changelog_text,
            'token': get_login_token()
        }

        response = requests.post("https://plugin.ankicollab.com/submitChangelog", json=payload)
        if response.status_code == 200:
            QMessageBox.information(self, "Information", response.text)
        else:
            QMessageBox.warning(self, "Error", "An unknown error occurred while publishing the changelog.")

        self.accept()
       

class DeletedNotesDialog(QDialog):
    def __init__(self, deleted_notes, deck_hash):
        super().__init__()
        local_name = get_local_deck_from_hash(deck_hash)
        self.setWindowTitle(f"AnkiCollab - Notes Removed from Deck {local_name}")
        self.setModal(True)

        layout = QVBoxLayout()

        label = QLabel("The maintainers removed the following notes from the deck. How do you want to proceed?\n")
        layout.addWidget(label)

        scroll_area = QScrollArea()

        deleted_notes_text = QTextBrowser()
        deleted_notes_text.setMaximumHeight(200)

        deleted_notes_str = "\n".join(map(str, deleted_notes))
        deleted_notes_text.setPlainText(deleted_notes_str)

        scroll_area.setWidget(deleted_notes_text)
        scroll_area.setWidgetResizable(True)  # Allow the QTextBrowser to expand within the scroll area

        layout.addWidget(scroll_area)

        button_box = QDialogButtonBox()
        delete_button = button_box.addButton("Delete Notes", QDialogButtonBox.ButtonRole.AcceptRole)
        open_in_browser_button = button_box.addButton("Show in Browser", QDialogButtonBox.ButtonRole.RejectRole)
        button_box.addButton("Keep Notes", QDialogButtonBox.ButtonRole.ActionRole)

        layout.addWidget(button_box)

        self.setLayout(layout)

        delete_button.clicked.connect(self.accept)
        open_in_browser_button.clicked.connect(self.reject)

        self.adjustSize()