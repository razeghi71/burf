from google.oauth2 import service_account
import os
import json
from os.path import expanduser


class CredentialsProvider:
    def __init__(self, config_file) -> None:
        self.config_file = expanduser(config_file)

    def _is_valid_service_account(self, file_name):
        if not os.path.exists(file_name):
            return False

        required_keys = [
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
            "client_id",
            "auth_uri",
            "token_uri",
        ]

        with open(file_name, "r") as file:
            file_content = file.read()

        try:
            json_data = json.loads(file_content)
        except json.JSONDecodeError:
            return False
        else:
            if all(key in json_data for key in required_keys):
                return True
            else:
                return False

    def to_credential(self, service_account_file):
        return service_account.Credentials.from_service_account_file(
            service_account_file
        )

    def get_current_service_accounts(self):
        with open(self.config_file, "r") as config_file:
            for service_account_file in config_file.readlines():
                service_account_file = service_account_file.strip()
                if self._is_valid_service_account(service_account_file):
                    yield self.to_credential(service_account_file)
