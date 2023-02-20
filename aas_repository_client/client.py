"""
Todo: Store password with keyring credential locker
"""
import json
from typing import Optional, Dict, List, Tuple

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

    def get_identifiable(self, identifier: model.Identifier, failsafe: bool = False) -> Optional[model.Identifiable]:
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

    def query_semantic_id(
            self,
            semantic_id: model.Key,
            check_for_key_type: bool = False,
            check_for_key_local: bool = False,
            check_for_key_id_type: bool = False
    ) -> List[Tuple[model.Identifier, Optional[model.Identifier]]]:
        """
        Query the repository server for a semanticID.
        Returns a tuple(
            Identifier of the Identifiable where the semanticID is contained (eg. a Submodel),
            Identifier of the parent AssetAdministrationShell, if exists
        )

        Note: Returns an empty list, if no results found.
        """
        response = requests.get(
            "{}/query_semantic_id".format(self.uri),
            headers=self.auth_headers,
            data=json.dumps(
                {
                    "semantic_id": semantic_id,
                    "check_for_key_type": check_for_key_type,
                    "check_for_key_local": check_for_key_local,
                    "check_for_key_id_type": check_for_key_id_type
                },
                cls=json_serialization.AASToJsonEncoder
            )
        )
        found_identifiers: List[Tuple[model.Identifier, Optional[model.Identifier]]] = []
        if response.status_code != 200:
            return found_identifiers
        found_identifier_data = json.loads(
            response.content,
            cls=json_deserialization.AASFromJsonDecoder
        )
        for data in found_identifier_data:
            identifier: model.Identifier = model.Identifier(
                id_=data["identifier"]["id"],
                id_type=json_deserialization.IDENTIFIER_TYPES_INVERSE[
                    data["identifier"]["idType"]]
            )
            aas_identifier: Optional[model.Identifier] = None
            if data["asset_administration_shell"] is not None:
                aas_identifier = model.Identifier(
                    id_=data["asset_administration_shell"]["id"],
                    id_type=json_deserialization.IDENTIFIER_TYPES_INVERSE[
                        data["asset_administration_shell"]["idType"]
                    ]
                )
            found_identifiers.append((identifier, aas_identifier))
        return found_identifiers


class AASRepositoryServerError(Exception):
    """
    Raised, if something went wrong when communicating with the server
    """
    pass


if __name__ == '__main__':
    client = AASRepositoryClient("http://127.0.0.1:2234", username="test")
    client.login(password="test")
    print(f"Received JWT: {client.token}")
    print(client.get_identifiable(model.Identifier(id_="https://example.com/sm/test_submodel03", id_type=model.IdentifierType.IRI)))
    print(client.query_semantic_id(model.Key(type_=model.KeyElements.GLOBAL_REFERENCE, local=False, value="https://example.com/semanticIDs/ONE", id_type=model.KeyType.IRI)))
