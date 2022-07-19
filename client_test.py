from aas_repository_client import client
from basyx.aas import model, adapter


if __name__ == '__main__':
    repo_client = client.AASRepositoryClient("http://127.0.0.1:2234", "test")
    repo_client.login("test")
    print(repo_client.token)
    print("Success")

    aas_id: model.Identifier = model.Identifier(
        id_="https://FLUIDON.com/AAS_Ram_Z1",
        id_type=model.IdentifierType.IRI
    )

    semantic_id_2 = model.Key(
        type_=model.KeyElements.GLOBAL_REFERENCE,
        local=False,
        value="https://example.com/semanticIDs/TWO",
        id_type=model.KeyType.IRI
    )

    # type_ = model.KeyElements.GLOBAL_REFERENCE,
    # local = False,
    # value = "https://example.com/semanticIDs/TWO",
    # id_type = model.KeyType.IRI

    property_sem_id = model.Key(
        type_=model.KeyElements.CONCEPT_DESCRIPTION, id_type=model.KeyType.IRDI, value="BASY-1#02-LPipe1#001", local=True
    )

    aas = repo_client.get_identifiable(identifier=aas_id)
    print(aas)

    # sm = repo_client.get_identifiable(identifier=sm_simulation_id)
    # print(sm)

    ident_semantic_id_2 = repo_client.query_semantic_id(semantic_id=semantic_id_2)
    print(ident_semantic_id_2)

    ident_property_sem_id = repo_client.query_semantic_id(semantic_id=property_sem_id)
    print(ident_property_sem_id)
