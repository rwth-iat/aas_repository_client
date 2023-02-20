"""
Todo: Store password with keyring credential locker
"""
import json
from typing import Optional, Dict, List, Tuple

import requests.auth

from basyx.aas import model
from basyx.aas.adapter.json import json_serialization, json_deserialization

import os


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
                    "Response status is not 200"
                )
        identifiable = json.loads(response.content, cls=json_deserialization.AASFromJsonDecoder)
        assert isinstance(identifiable, model.Identifiable)
        return identifiable

    def modify_identifiable(self, identifiable: model.Identifiable,
                            failsafe: bool = False) -> Optional[model.Identifier]:
        """
        Modify an Identifiable from the repository server

        :param identifiable: Identifiable
        :param failsafe: If True, return None, if the Identifiable is not found. Otherwise an error is raised
        :return: The Identifier of the modified Identifiable
        """
        response = requests.put(
            "{}/modify_identifiable".format(self.uri),
            headers=self.auth_headers,
            data=json.dumps(identifiable, cls=json_serialization.AASToJsonEncoder)
        )
        if response.status_code != 200:
            if failsafe:
                return None
            else:
                raise AASRepositoryServerError(
                    "Could not fetch Identifiable with id {} from the server {}: {}".format(
                        identifiable.identification.id,
                        self.uri,
                        response.content.decode("utf-8")
                    )
                )
        return identifiable.identification

    def add_identifiable(self, identifiable: model.Identifiable,
                         failsafe: bool = False) -> Optional[model.Identifier]:
        """
        Add an Identifiable to the repository server

        :param identifiable: Identifiable
        :param failsafe: If True, return None, if the Identifiable is not found. Otherwise an error is raised
        :return: The Identifier of the added Identifiable
        """
        response = requests.post(
            "{}/add_identifiable".format(self.uri),
            headers=self.auth_headers,
            data=json.dumps(identifiable, cls=json_serialization.AASToJsonEncoder)
        )
        if response.status_code != 200:
            if failsafe:
                return None
            else:
                raise AASRepositoryServerError(
                    "Could not add Identifiable with id {} to the server {}: {}".format(
                        identifiable.identification.id,
                        self.uri,
                        response.content.decode("utf-8")
                    )
                )
        return identifiable.identification

    def get_file(self, file_iri: str, save_as: str, failsafe: bool = False):
        """
        Get an File from the repository server via its IRI

        :param file_iri: IRI of the File
        :param failsafe: If True, return None, if no File to the IRI is found.
            Otherwise, raise an `AASRepositoryServerError`
        :param save_as: The location (folder and filename) of where the file should be
            saved on the local machine.
        :return: The IRI
        """
        response = requests.get(
            "{}/get_fmu".format(self.uri),
            headers=self.auth_headers,
            data=json.dumps(file_iri)
        )
        if response.status_code != 200:
            if failsafe:
                return None
            else:
                raise AASRepositoryServerError(
                    "Could not fetch FMU-File with id {} from the server {}: {}".format(
                        file_iri,
                        self.uri,
                        response.content.decode("utf-8")
                    )
                )
        with open(save_as, 'wb', buffering=4096) as file:
            file.write(response.content)
        return file_iri

    def add_file(self, file_path: str, failsafe: bool = False):
        """
        Add a File to the repository server

        :param file_path: The Path to the File
        :param failsafe: If True, return None, if the File is not added.
            Otherwise, raise an `AASRepositoryServerError`
        :return: The IRI of the added File
        """
        header_with_name = self.auth_headers
        header_with_name["name"] = file_path.split('/')[-1]
        if not os.path.isfile(file_path):
            raise FileNotFoundError(
                "Could not find file in {}".format(
                    file_path
                )
            )

        def generate():
            with open(file_path, mode='rb', buffering=4096) as file:
                for chunk in file:
                    yield chunk
        response = requests.post(
            "{}/post_file".format(self.uri),
            headers=header_with_name,
            data=generate())
        if response.status_code != 200:
            if failsafe:
                return None
            else:
                raise AASRepositoryServerError(
                    "Could not add FMU {} to the server {}: {}".format(
                        header_with_name["name"],
                        self.uri,
                        response.content.decode("utf-8")
                    )
                )
        return response.content.decode()

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
    client.add_identifiable(
        model.Submodel(
            identification=model.Identifier(
                id_="https://acplt.org/ExampleSubmodel15",
                id_type=model.IdentifierType.IRI
            ),
            id_short="ExampleSubmodel15",
            semantic_id=model.Reference(tuple([
                model.Key(
                    type_=model.KeyElements.GLOBAL_REFERENCE,
                    local=False,
                    value="http://acplt.org/ExampleSemanticID",
                    id_type=model.KeyType.IRI
                )
            ]))
        )
    )
    client.add_identifiable(
        model.Submodel(
            identification=model.Identifier(
                id_="https://acplt.org/ExampleSubmodel16",
                id_type=model.IdentifierType.IRI
            ),
            id_short="ExampleSubmodel15",
            semantic_id=model.Reference(tuple([
                model.Key(
                    type_=model.KeyElements.GLOBAL_REFERENCE,
                    local=False,
                    value="http://acplt.org/ExampleSemanticID",
                    id_type=model.KeyType.IRI
                )
            ]))
        )
    )
    print(client.query_semantic_id(
        model.Key(
            type_=model.KeyElements.GLOBAL_REFERENCE,
            local=False,
            value="http://acplt.org/ExampleSemanticID",
            id_type=model.KeyType.IRI
        )
    ))
