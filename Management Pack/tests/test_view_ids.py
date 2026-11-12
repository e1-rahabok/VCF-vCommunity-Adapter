#  Copyright 2026 VCF Operations vCommunity Management Pack
"""The pack must not ship a view under the id of a view built into VCF Operations.

VCF Operations imports a view by id. A view in the pack with a built-in id replaces the built-in view when the pack is
installed, and the built-in view is deleted when the pack is uninstalled or when an upgrade no longer ships it. The ids
below are the built-in views that earlier versions of the pack shipped, found by comparing the pack with content exports
of VCF Operations 8.18.7 and 9.1.1. There are 120: 117 that the upstream pack shipped, and three more that were added in
this repository (the VCF Management Services views, which are built-in views of 9.1.1 and are not in the 8.18.7 export).
See "Upgrade from a version that shipped built-in view ids" in
docs/installation-guide/installation.md.

Every viewDefinitionId in a dashboard must name a view the pack ships, or a built-in view on the allowlist below.
The 19 views that are no longer shipped stay on the allowlist so that nothing re-adds them or points a widget at an id
that no longer exists.

Run from the "Management Pack" folder:  python -m pytest tests
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

CONTENT = Path(__file__).resolve().parents[1] / "content"

BUILT_IN_VIEW_IDS = frozenset({
    "02230501-23d6-4512-858e-381d60876e73",
    "0a898851-197b-4e82-baf6-a2a89acd600a",
    "0ef97d2c-770b-4c74-9c82-28a766164a39",
    "0f5cd0c6-a06c-4be0-9af1-16adc6eac7ac",
    "11dd432d-6c6f-4872-8c0a-2d9975856f66",
    "16d4447f-ae24-4d6d-b4ef-c5f2a3321351",
    "19729c38-20e3-4fea-bb9f-0576126c25ec",
    "1fa18cd9-f908-4120-9c81-797282a3db37",
    "23b3812d-fac8-449a-acb7-488a388a0716",
    "2486078e-790e-485b-8ab5-70c1da351a0d",
    "24bd3eec-5fe8-4a90-9ad9-fa570b791973",
    "2788178d-7df4-47d7-81de-016f7a1cd18d",
    "27f6a2e8-ddac-4dc2-b3bf-5f222af701db",
    "2805f0a4-e58b-432b-861d-cffe1604fbfc",
    "3a424415-c06f-4b5b-b742-5b8d25c7e5ba",
    "3a88e1a7-511c-440d-868b-65df4a2c7898",
    "3b0e097b-b3f1-453f-adc9-ad47c9c5ca4c",
    "3b33a0a0-d830-4640-8635-f1857bcb5ffd",
    "3b6b0e60-7924-4d26-9a11-5fdde36e8a77",
    "3c32ba9d-e71c-4f2c-bf46-844d1b07857f",
    "3ede5e0a-2121-4579-a250-26648589cb4a",
    "40152c12-1d12-440c-b79e-e9d172deb9a1",
    "40b1d206-8616-47e2-9bee-6142b4427180",
    "40c5bbc9-db9d-468c-8094-2137d22e53a7",
    "40e416d0-0ee4-4aa2-9ad6-93d162f668a0",
    "41127d01-e62b-4d46-89d4-7293ed86103c",
    "42f8a97e-048a-4cb2-82cc-db121958722c",
    "45281acb-5643-4a0c-b4d2-300548289b89",
    "493527e2-d992-4e56-98ae-d9245c255174",
    "49b13b68-dee2-483d-8df8-1b6d7957d01c",
    "4d1155bd-cb97-41b3-896f-843db27775fe",
    "4d71034d-6368-4284-be94-94887f87eddc",
    "4d9b6ad6-3325-42ff-8593-77793e547a4d",
    "51ea3aa0-2671-44da-ac00-8c265767ad83",
    "524d0468-8f9d-460b-a2a5-95c2d8846661",
    "56abf797-0534-4b73-bc27-693317a206ac",
    "5c20ba39-9d8b-4272-b01d-8dbafeded995",
    "5c3441f2-4619-441c-ad02-0b01ead34813",
    "5fc79159-ddc9-4f38-8dc6-461c79b379f4",
    "614c2d3f-98f0-4862-8dcd-fd6b0b4c799d",
    "617644c5-bb68-43e0-b388-057358525ec6",
    "653ba701-c9df-4f98-9dd1-8b1d6b57612e",
    "680f4627-e5c6-4ac5-8c54-87f02ad2b122",
    "6c06a467-d9b3-4965-8164-4e5c43940924",
    "6d865efb-5dcd-496f-9a07-ced99f530142",
    "6db204b2-0315-4488-8cbc-bbe33c74dac9",
    "6dbbe2bc-2593-4288-9d4c-23995e28009d",
    "6efeb9b2-3c38-4842-8ee9-88f6b25e5460",
    "6f0a54e7-c3a5-42bb-a989-fda47cf1c50a",
    "72cefd21-9a01-45e6-a33c-ea2a6897ac5d",
    "74639bd8-2ece-4032-b22f-ffc23e65598f",
    "7888104e-2210-4539-a589-8cefa7a0361d",
    "7bb1bf81-8895-4008-b770-5c7fc106c22a",
    "7bcb4d10-700f-4bee-94f1-03ffada5ae65",
    "7bcdb50d-c015-4237-9014-832a74f07f91",
    "7d0d858d-628d-49e9-b076-4fb15d757cc3",
    "7e913396-7712-438c-a22f-97140fea9892",
    "8161f003-c456-47b2-9ce3-b88affa8c7d1",
    "81ef5dfc-b519-4981-8a8e-ee1dbb516aca",
    "850c16a9-3fa6-416a-a4e2-35a6509928aa",
    "86d58689-64de-4faf-9a53-2425decfe6a6",
    "87399ea9-d93a-4591-b15b-d30a9003972e",
    "8986cc9d-5a60-407d-bdbf-25a1bc082b18",
    "8d44e30e-9bb1-4df1-bf1f-8d2f44276af4",
    "8d497409-b506-4027-bc22-27cda696116e",
    "9030cd79-ee63-42a2-9f03-7b2ac3f56d22",
    "90f20c54-20c2-499c-8fb2-c609e65c325c",
    "94b25c6a-bc08-4b7f-83e5-d55d4b6d89e1",
    "95416c42-b863-415c-88b8-c5294f43daa1",
    "97e71e70-094d-435d-b4f4-99da4e489ec2",
    "9911f98d-0e2a-4d4f-aefe-973e28ecf1cc",
    "998cf7f2-b636-4ac5-96b2-833c81f3097c",
    "9a556ea6-db06-4ad5-b1a1-84bb1ae7032e",
    "9a77a4b5-0329-459c-9f42-7087f0d911a6",
    "9d5498ba-848f-4d23-8b6e-765a566a0659",
    "9e427b59-a30a-475c-bafc-a1943d9f2f0d",
    "a3849f91-76c6-4791-81d7-65245e321233",
    "a62de769-9b4b-462e-906c-b4a27457ec88",
    "a8b54a14-038c-4f1b-ab93-1cc0a6f4bc00",
    "acb921e6-525a-41b6-bcd7-4a8e972f2acc",
    "ad2f56bc-3a78-4045-b2b5-c953781b5c76",
    "b5f3660a-082c-4af9-b89e-bc670d932e99",
    "b8af9e79-a062-4e3b-8501-7bbc64a6a3f9",
    "b963d4b9-12ba-41a2-86df-9e294a1c5f66",
    "ba5d47b2-2a6d-4f19-8e11-105fb13c5bf9",
    "bf0d0ad1-53d5-42d7-a1a1-67f908642d5d",
    "bf6bb2c6-12e3-417e-916f-70ab5ec411ad",
    "c0b7e702-f550-4223-808c-aa14b35117a9",
    "c20dadab-e990-4917-aa75-04d8433da27e",
    "c655b25c-42be-4512-9c9b-8b4d6beefd71",
    "c94b11bf-18c5-41c4-80fe-26ae5882dd45",
    "c9fe7a11-79e3-4e98-9cba-8d732b15d150",
    "ccfc42fb-aaf3-439e-8111-3a0f1bf7713a",
    "cd6c06c5-7ac5-4edc-a2c8-5b8777512d59",
    "d1ba847b-582f-427f-b041-feab824feaa8",
    "d4ba9e73-bc26-4f5f-8cef-504a37cfc988",
    "d5b58361-bd8e-4102-969a-e4d9f887bcc0",
    "d975edde-111b-4e32-b63d-49df26a65cb1",
    "dadb69af-f77f-4644-8355-588f41c2f4f0",
    "de04afbf-832d-4bb9-a13c-c7680356c00f",
    "de1ff68b-1a78-4939-996d-600b0abef33e",
    "df2e3054-5db5-478f-bb7d-fbcaccd7960e",
    "e041c79b-910f-477b-9d7a-d84e495119cb",
    "e0e0972a-2da0-4544-a53f-9e55b09c74a3",
    "e2d1f3c7-336f-4eeb-80a1-144d1252bc5e",
    "e95aa10d-43c8-4d8a-bfda-2e4eb97996da",
    "ea6cf8d9-087a-4882-b98b-9acd2d4021ed",
    "ed44775e-bdbb-4342-a077-3d98f0250cf9",
    "f129ab04-a919-4b80-b0ad-39783db28adf",
    "f1474ada-0abe-4e6b-937a-ec4e7d82e420",
    "f752ddef-406d-4868-bd78-8b00aaa425cc",
    "f83a4c60-9931-4305-95f9-93f724be86fe",
    "f982ee15-5502-49e2-8efc-0a405b5bfa83",
    "fa10900c-2d88-41d6-86c9-046349ccc5bf",
    "fc20d8a6-9f74-4b78-9022-7441c6d877e9",
    "fc64c67a-d5b0-4a03-a10b-767b9b247120",
    "fcab0100-1881-48b6-bd07-aaeaa3ee669e",
    # Added in this repository, not in the upstream 117: built-in views of 9.1.1, absent from an 8.18.7 export.
    "4747af30-e22c-44b8-b2cf-e206e7310f12",  # VCF Management Services Nodes View
    "cadb4cc0-aba9-4ca1-a035-64a0d0cae5c1",  # VCF Management Services Volumes View
    "df8479d3-45c0-4e1a-9cb3-9c3412f93579",  # VCF Management Services Components View
})

# Built-in views that the pack's dashboards name in viewDefinitionId on purpose, and does not ship.
# The first 19 are views that earlier versions shipped as copies of the built-in view and that are no longer shipped.
# The rest are built-in views that the dashboards already used.
REFERENCED_BUILT_IN_VIEW_IDS = frozenset({
    # No longer shipped: the dashboards use the built-in view.
    "0a898851-197b-4e82-baf6-a2a89acd600a",
    "11dd432d-6c6f-4872-8c0a-2d9975856f66",
    "3b33a0a0-d830-4640-8635-f1857bcb5ffd",
    "40152c12-1d12-440c-b79e-e9d172deb9a1",
    "42f8a97e-048a-4cb2-82cc-db121958722c",
    "4d1155bd-cb97-41b3-896f-843db27775fe",
    "653ba701-c9df-4f98-9dd1-8b1d6b57612e",
    "6dbbe2bc-2593-4288-9d4c-23995e28009d",
    "7bcdb50d-c015-4237-9014-832a74f07f91",
    "90f20c54-20c2-499c-8fb2-c609e65c325c",
    "a62de769-9b4b-462e-906c-b4a27457ec88",
    "acb921e6-525a-41b6-bcd7-4a8e972f2acc",
    "b963d4b9-12ba-41a2-86df-9e294a1c5f66",
    "c0b7e702-f550-4223-808c-aa14b35117a9",
    "c9fe7a11-79e3-4e98-9cba-8d732b15d150",
    "d5b58361-bd8e-4102-969a-e4d9f887bcc0",
    "d975edde-111b-4e32-b63d-49df26a65cb1",
    "e95aa10d-43c8-4d8a-bfda-2e4eb97996da",
    "ed44775e-bdbb-4342-a077-3d98f0250cf9",
    # Built-in views that the dashboards already used before this change.
    "12fd58e7-82bf-402d-a173-60702566a124",
    "421ac1e1-91a0-4752-a0fd-5cebad574041",
    "4c335172-0eb4-4b8e-b019-7bdf51f5ed57",
    "55bbf293-771b-470d-be60-0c678c96fcd8",
    "75f7a278-6dd9-425c-abce-b1fbb75fc82b",
    "80fd0aba-ee23-4247-b020-c35c4ac3d73b",
    "867d0405-3f05-49ee-9466-ede29a147aff",
    "a245c324-5359-4255-9762-3edd16ab9f30",
    "d3487e74-223e-402c-9e90-6b6d5987a541",
    "d8a3767e-9d5e-4bf2-b613-9e3bef977502",
    "da47d6b5-ea3f-44cc-aea4-fb7e51c77d93",
    "e3321b7e-033e-4a5e-820f-796d38b268f5",
    "e6cd13d9-02af-4252-af46-1f8402cc3296",
    "f2a01570-7335-4e0f-b203-4999052658c3",
    "f60469d1-57d0-4dd2-84d0-7ffc36d9d86b",
    "ff9f60e3-65a7-4b3d-a41f-842517aee5b0",
})


def _shipped_views():
    """Every ViewDef in the content folder, as (file name, element)."""
    views = []
    for path in sorted(CONTENT.rglob("*.xml")):
        for view in ET.parse(path).getroot().iter("ViewDef"):
            views.append((path.name, view))
    return views


def _same_view(view):
    """The view as text, without the ids of its controls and data providers, which differ between exports."""
    parts = []
    for element in view.iter():
        attributes = dict(element.attrib)
        if element.tag in ("Control", "DataProvider"):
            attributes.pop("id", None)
        parts.append((element.tag, tuple(sorted(attributes.items())), (element.text or "").strip()))
    return tuple(parts)


def test_the_list_is_120_distinct_ids():
    assert len(BUILT_IN_VIEW_IDS) == 120


def test_no_shipped_view_has_the_id_of_a_built_in_view():
    clashes = sorted({(name, view.get("id")) for name, view in _shipped_views() if view.get("id") in BUILT_IN_VIEW_IDS})
    assert clashes == []


def test_a_view_defined_in_several_files_is_the_same_view_in_each():
    copies = {}
    for name, view in _shipped_views():
        copies.setdefault(view.get("id"), {}).setdefault(_same_view(view), []).append(name)
    differing = {view_id: sorted(sum(versions.values(), [])) for view_id, versions in copies.items() if len(versions) > 1}
    assert differing == {}


def _referenced_view_ids():
    """Every viewDefinitionId in the dashboards, as (file name, id)."""
    references = []
    for path in sorted(CONTENT.rglob("*.json")):
        for view_id in re.findall(r'"viewDefinitionId"\s*:\s*"([^"]+)"', path.read_text(encoding="utf-8")):
            references.append((path.name, view_id))
    return references


def test_the_allowlist_holds_built_in_views_the_pack_does_not_ship():
    shipped = {view.get("id") for _, view in _shipped_views()}
    assert sorted(shipped & REFERENCED_BUILT_IN_VIEW_IDS) == []
    dropped = REFERENCED_BUILT_IN_VIEW_IDS & BUILT_IN_VIEW_IDS
    assert len(dropped) == 19


def test_every_view_a_dashboard_uses_is_shipped_or_an_allowed_built_in_view():
    known = {view.get("id") for _, view in _shipped_views()} | REFERENCED_BUILT_IN_VIEW_IDS
    unknown = sorted({(name, view_id) for name, view_id in _referenced_view_ids() if view_id not in known})
    assert unknown == []
