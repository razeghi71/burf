import os
import json

from google.oauth2 import service_account

from typing import Iterator


class CredentialsProvider:
    def __init__(self, config_file: str) -> None:
        self.config_file = os.path.expanduser(config_file)

    def _is_valid_service_account(self, file_name: str) -> bool:
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

    def to_credential(self, service_account_file: str) -> service_account.Credentials:
        return service_account.Credentials.from_service_account_file(
            service_account_file
        )

    def add_service_account(self, service_account_file: str) -> None:
        if self._is_valid_service_account(service_account_file):
            with open(self.config_file, "r+") as file:
                accounts = map(lambda x: x.strip(), file.readlines())
                if str(service_account_file) not in accounts:
                    file.write(str(service_account_file) + "\n")

    def get_current_service_accounts(self) -> Iterator[service_account.Credentials]:
        with open(self.config_file, "r") as config_file:
            for service_account_file in config_file.readlines():
                service_account_file = service_account_file.strip()
                if self._is_valid_service_account(service_account_file):
                    yield self.to_credential(service_account_file)
