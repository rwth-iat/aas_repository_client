"""
Todo: Store password with keyring credential locker
"""
import json
from typing import Optional, Dict, List

import requests.auth

from basyx.aas import model
from basyx.aas.adapter.json import json_serialization, json_deserialization


class AASRepositoryClient:
    def __init__(self,
                 uri: str,
                 username: str):
        """
        Initializer for class AASRepositoryClient

        :param uri: URI to the AAS Repository Server
        :param username: Username
        """
        self.uri: str = uri
        self.username: str = username
        self.token: Optional[str] = None
        self.auth_headers: Optional[Dict[str, str]] = None

    def login(self, password: str):
        """
        Log in with the given password and store the token in this class

        :param password: Password to the user
        """
        response: requests.Response = requests.get(
            "{}/login".format(self.uri),
            auth=requests.auth.HTTPBasicAuth(username=self.username, password=password)
        )
        self.token = json.loads(response.content)["token"]
        self.auth_headers = {"x-access-tokens": self.token}

    def get_identifiable(self, identifier: model.Identifier, failsafe: bool = False) -> Optional[model.Identifier]:
        """
        Get an Identifiable from the repository server via its Identifier

        :param identifier: Identifier of the Identifiable
        :param failsafe: If True, return None, if the Identifiable is not found. Otherwise an error is raised
        :return: The Identifier
        """
        response = requests.get(
            "{}/get_identifiable".format(self.uri),
            headers=self.auth_headers,
            data=json.dumps(identifier, cls=json_serialization.AASToJsonEncoder)
        )
        if response.status_code != 200:
            if failsafe:
                return None
            else:
                raise AASRepositoryServerError(
                    "Could not fetch Identifiable with id {} from the server {}: {}".format(
                        identifier.id,
                        self.uri,
                        response.content.decode("utf-8")
                    )
                )
        identifiable = json.loads(response.content, cls=json_deserialization.AASFromJsonDecoder)
        assert isinstance(identifiable, model.Identifiable)
        return identifiable

    def query_semantic_id(self, semantic_id: model.Key) -> List[model.Identifier]:
        """
        Query the repository server for a semanticID. Returns Identifiers for all Identifiable objects that contain
        the given semanticID.

        Note: Returns an empty list, if no Identifiables found,
        """
        response = requests.get(
            "{}/get_identifiable".format(self.uri),
            headers=self.auth_headers,
            data=json.dumps(semantic_id, cls=json_serialization.AASToJsonEncoder)
        )
        found_identifiers: List[model.Identifier] = []
        if response.status_code != 200:
            return found_identifiers
        found_identifiers.extend(json.loads(response.content, cls=json_deserialization.AASFromJsonDecoder))
        for identifier in found_identifiers:
            assert isinstance(identifier, model.Identifier)
        return found_identifiers


class AASRepositoryServerError(Exception):
    """
    Raised, if something went wrong when communicating with the server
    """
    pass


if __name__ == '__main__':
    client = AASRepositoryClient("http://127.0.0.1:2234", "test")
    client.login("test")
    print(client.token)
