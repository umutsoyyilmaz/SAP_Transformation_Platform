"""
FAZ 9 — Custom Fields & Layout Engine — Tests
~40 tests covering field definitions, field values, layout configs, set-default, model integrity.
"""

import pytest


API = "/api/v1"


def _post(client, url, data=None):
    return client.post(API + url, json=data or {})


def _get(client, url):
    return client.get(API + url)


def _put(client, url, data=None):
    return client.put(API + url, json=data or {})


def _delete(client, url):
    return client.delete(API + url)


# ── fixtures ──

@pytest.fixture()
def program(client):
    res = _post(client, "/programs", {"name": "F9 Test Program"})
    assert res.status_code == 201
    return res.get_json()


@pytest.fixture()
def field_def(client, program):
    res = _post(
        client,
        f"/programs/{program['id']}/custom-fields",
        {
            "field_name": "priority_level",
            "field_label": "Priority Level",
            "field_type": "select",
            "entity_type": "test_case",
            "options": [
                {"value": "low", "label": "Low"},
                {"value": "medium", "label": "Medium"},
                {"value": "high", "label": "High"},
            ],
            "is_required": True,
            "sort_order": 1,
        },
    )
    assert res.status_code == 201
    return res.get_json()["field"]


@pytest.fixture()
def layout(client, program):
    res = _post(
        client,
        f"/programs/{program['id']}/layouts",
        {
            "name": "Default TC Layout",
            "entity_type": "test_case",
            "sections": [
                {
                    "id": "basic",
                    "title": "Basic Info",
                    "visible": True,
                    "sort_order": 0,
                    "fields": ["title", "description"],
                },
                {
                    "id": "custom",
                    "title": "Custom Fields",
                    "visible": True,
                    "sort_order": 1,
                    "fields": [],
                },
            ],
        },
    )
    assert res.status_code == 201
    return res.get_json()["layout"]


# ═══════════════════════════════════════════════════════════════
#  9.1  Custom Field Definitions
# ═══════════════════════════════════════════════════════════════


class TestFieldDefinitions:
    def test_create_field(self, client, program):
        res = _post(
            client,
            f"/programs/{program['id']}/custom-fields",
            {"field_name": "env_tag", "field_type": "text"},
        )
        assert res.status_code == 201
        f = res.get_json()["field"]
        assert f["field_name"] == "env_tag"
        assert f["field_type"] == "text"
        assert f["entity_type"] == "test_case"

    def test_create_field_requires_name(self, client, program):
        res = _post(
            client,
            f"/programs/{program['id']}/custom-fields",
            {"field_type": "text"},
        )
        assert res.status_code == 400

    def test_duplicate_field_name_rejected(self, client, program, field_def):
        res = _post(
            client,
            f"/programs/{program['id']}/custom-fields",
            {"field_name": "priority_level", "entity_type": "test_case"},
        )
        assert res.status_code == 409

    def test_list_fields(self, client, program, field_def):
        res = _get(client, f"/programs/{program['id']}/custom-fields")
        assert res.status_code == 200
        assert res.get_json()["total"] >= 1

    def test_list_fields_filter_entity(self, client, program, field_def):
        # Create a defect field
        _post(
            client,
            f"/programs/{program['id']}/custom-fields",
            {"field_name": "severity", "entity_type": "defect"},
        )
        res = _get(
            client,
            f"/programs/{program['id']}/custom-fields?entity_type=defect",
        )
        assert res.status_code == 200
        for f in res.get_json()["fields"]:
            assert f["entity_type"] == "defect"

    def test_get_field(self, client, field_def):
        res = _get(client, f"/custom-fields/{field_def['id']}")
        assert res.status_code == 200
        assert res.get_json()["field"]["field_name"] == "priority_level"

    def test_update_field(self, client, field_def):
        res = _put(
            client,
            f"/custom-fields/{field_def['id']}",
            {"field_label": "Updated Label", "is_required": False},
        )
        assert res.status_code == 200
        assert res.get_json()["field"]["field_label"] == "Updated Label"
        assert res.get_json()["field"]["is_required"] is False

    def test_delete_field(self, client, field_def):
        res = _delete(client, f"/custom-fields/{field_def['id']}")
        assert res.status_code == 200
        res2 = _get(client, f"/custom-fields/{field_def['id']}")
        assert res2.status_code == 404

    def test_field_404(self, client):
        res = _get(client, "/custom-fields/99999")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════
#  9.1b  Custom Field Values
# ═══════════════════════════════════════════════════════════════


class TestFieldValues:
    def test_set_entity_values(self, client, field_def):
        res = _post(
            client,
            "/custom-fields/values/test_case/1",
            {"values": {str(field_def["id"]): "high"}},
        )
        assert res.status_code == 200
        vals = res.get_json()["values"]
        assert len(vals) >= 1
        assert vals[0]["value"] == "high"

    def test_get_entity_values(self, client, field_def):
        _post(
            client,
            "/custom-fields/values/test_case/42",
            {"values": {str(field_def["id"]): "medium"}},
        )
        res = _get(client, "/custom-fields/values/test_case/42")
        assert res.status_code == 200
        assert res.get_json()["entity_id"] == 42
        assert len(res.get_json()["values"]) >= 1

    def test_upsert_values(self, client, field_def):
        # Set initial
        _post(
            client,
            "/custom-fields/values/test_case/10",
            {"values": {str(field_def["id"]): "low"}},
        )
        # Update
        res = _post(
            client,
            "/custom-fields/values/test_case/10",
            {"values": {str(field_def["id"]): "high"}},
        )
        assert res.status_code == 200
        assert res.get_json()["values"][0]["value"] == "high"

    def test_update_single_value(self, client, field_def):
        cr = _post(
            client,
            "/custom-fields/values/test_case/20",
            {"values": {str(field_def["id"]): "low"}},
        )
        vid = cr.get_json()["values"][0]["id"]
        res = _put(client, f"/custom-field-values/{vid}", {"value": "updated"})
        assert res.status_code == 200
        assert res.get_json()["value"]["value"] == "updated"

    def test_delete_value(self, client, field_def):
        cr = _post(
            client,
            "/custom-fields/values/test_case/30",
            {"values": {str(field_def["id"]): "del_me"}},
        )
        vid = cr.get_json()["values"][0]["id"]
        res = _delete(client, f"/custom-field-values/{vid}")
        assert res.status_code == 200

    def test_list_field_values(self, client, field_def):
        _post(
            client,
            "/custom-fields/values/test_case/50",
            {"values": {str(field_def["id"]): "v1"}},
        )
        _post(
            client,
            "/custom-fields/values/test_case/51",
            {"values": {str(field_def["id"]): "v2"}},
        )
        res = _get(client, f"/custom-fields/{field_def['id']}/values")
        assert res.status_code == 200
        assert len(res.get_json()["values"]) >= 2

    def test_set_values_requires_dict(self, client, field_def):
        res = _post(client, "/custom-fields/values/test_case/99", {})
        assert res.status_code == 400

    def test_value_404(self, client):
        res = _put(client, "/custom-field-values/99999", {"value": "x"})
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════
#  9.2  Layout Configs
# ═══════════════════════════════════════════════════════════════


class TestLayoutConfigs:
    def test_create_layout(self, client, program):
        res = _post(
            client,
            f"/programs/{program['id']}/layouts",
            {
                "name": "Compact View",
                "entity_type": "test_case",
                "sections": [{"id": "s1", "title": "Info", "visible": True}],
            },
        )
        assert res.status_code == 201
        l = res.get_json()["layout"]
        assert l["name"] == "Compact View"
        assert len(l["sections"]) == 1

    def test_create_layout_requires_name(self, client, program):
        res = _post(
            client,
            f"/programs/{program['id']}/layouts",
            {"sections": []},
        )
        assert res.status_code == 400

    def test_list_layouts(self, client, program, layout):
        res = _get(client, f"/programs/{program['id']}/layouts")
        assert res.status_code == 200
        assert res.get_json()["total"] >= 1

    def test_get_layout(self, client, layout):
        res = _get(client, f"/layouts/{layout['id']}")
        assert res.status_code == 200
        assert res.get_json()["layout"]["name"] == "Default TC Layout"

    def test_update_layout(self, client, layout):
        res = _put(
            client,
            f"/layouts/{layout['id']}",
            {"name": "Updated Layout", "sections": [{"id": "a", "title": "A"}]},
        )
        assert res.status_code == 200
        assert res.get_json()["layout"]["name"] == "Updated Layout"

    def test_delete_layout(self, client, layout):
        res = _delete(client, f"/layouts/{layout['id']}")
        assert res.status_code == 200
        res2 = _get(client, f"/layouts/{layout['id']}")
        assert res2.status_code == 404

    def test_layout_404(self, client):
        res = _get(client, "/layouts/99999")
        assert res.status_code == 404


class TestSetDefaultLayout:
    def test_set_default(self, client, program):
        l1 = _post(
            client,
            f"/programs/{program['id']}/layouts",
            {"name": "L1", "entity_type": "test_case"},
        ).get_json()["layout"]
        l2 = _post(
            client,
            f"/programs/{program['id']}/layouts",
            {"name": "L2", "entity_type": "test_case"},
        ).get_json()["layout"]

        # Set L1 as default
        res = _post(client, f"/layouts/{l1['id']}/set-default")
        assert res.status_code == 200
        assert res.get_json()["layout"]["is_default"] is True

        # Set L2 as default — L1 should be unset
        res2 = _post(client, f"/layouts/{l2['id']}/set-default")
        assert res2.status_code == 200
        assert res2.get_json()["layout"]["is_default"] is True

        # Verify L1 no longer default
        check = _get(client, f"/layouts/{l1['id']}")
        assert check.get_json()["layout"]["is_default"] is False

    def test_set_default_404(self, client):
        res = _post(client, "/layouts/99999/set-default")
        assert res.status_code == 404


# ═══════════════════════════════════════════════════════════════
#  Model Integrity
# ═══════════════════════════════════════════════════════════════


class TestModelIntegrity:
    def test_field_to_dict(self, client, field_def):
        required = {
            "id", "field_name", "field_label", "field_type",
            "entity_type", "is_required", "is_filterable", "sort_order",
        }
        assert required.issubset(set(field_def.keys()))

    def test_value_to_dict(self, client, field_def):
        cr = _post(
            client,
            "/custom-fields/values/test_case/100",
            {"values": {str(field_def["id"]): "test_val"}},
        )
        val = cr.get_json()["values"][0]
        required = {"id", "field_id", "entity_type", "entity_id", "value"}
        assert required.issubset(set(val.keys()))

    def test_layout_to_dict(self, client, layout):
        required = {
            "id", "name", "entity_type", "sections",
            "is_default", "created_by",
        }
        assert required.issubset(set(layout.keys()))

    def test_cascade_delete_field_removes_values(self, client, program, field_def):
        # Add values
        _post(
            client,
            "/custom-fields/values/test_case/200",
            {"values": {str(field_def["id"]): "val1"}},
        )
        # Delete field definition
        res = _delete(client, f"/custom-fields/{field_def['id']}")
        assert res.status_code == 200
        # Values for that entity should be empty now
        vals = _get(client, "/custom-fields/values/test_case/200")
        assert len(vals.get_json()["values"]) == 0

    def test_field_options_json(self, client, field_def):
        """Verify options are stored as JSON list."""
        res = _get(client, f"/custom-fields/{field_def['id']}")
        opts = res.get_json()["field"]["options"]
        assert isinstance(opts, list)
        assert len(opts) == 3
        assert opts[0]["value"] == "low"
