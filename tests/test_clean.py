from sg_mockgun.clean import clean_schema


def field(data_type="text", hideable=True, valid_types=None):
    f = {
        "data_type": {"value": data_type, "editable": False},
        "visible": {"value": True, "editable": hideable},
        "properties": {"default_value": {"value": None, "editable": True}},
    }
    if valid_types is not None:
        f["properties"]["valid_types"] = {"value": valid_types, "editable": True}
    return f


def entity(name, visible=True):
    return {"name": {"value": name, "editable": True}, "visible": {"value": visible, "editable": True}}


def site():
    schema = {
        "Shot": {
            "code": field(hideable=False),
            "sg_status_list": field("status_list", hideable=False),
            "sg_head_in": field("number"),  # template field, hideable, upstream has it
            "sg_fp_test_checkbox": field("checkbox"),  # probe litter
            "platform_status": field(),  # stock, hideable, no sg_ prefix
            "shot_sg_lineage_shots": field("multi_entity"),  # reverse side of a custom link
            "sg_take": field("entity", hideable=False, valid_types=["CustomEntity09", "Asset"]),
        },
        "Asset": {"code": field(hideable=False)},
        "CustomEntity09": {"code": field(hideable=False)},
        "CustomEntity09_sg_photos_Connection": {"id": field("number", hideable=False)},
        "Asset_sg_vendor_groups_Connection": {"id": field("number", hideable=False)},
        "CustomEntity12": {"code": field(hideable=False)},
    }
    entities = {
        "Shot": entity("Shot"),
        "Asset": entity("Asset"),
        "CustomEntity09": entity("Take"),
        "CustomEntity09_sg_photos_Connection": entity("Custom Entity09 Sg Photos Connection"),
        "Asset_sg_vendor_groups_Connection": entity("Asset Sg Vendor Groups Connection"),
        "CustomEntity12": entity("Custom Entity12", visible=False),
    }
    return schema, entities


UPSTREAM = {"Shot": {"code": {}, "sg_head_in": {}}, "Asset": {"code": {}}}


def test_keeps_stock_and_upstream_fields_drops_the_rest():
    schema, _, report = clean_schema(*site(), UPSTREAM)
    assert set(schema["Shot"]) == {"code", "sg_status_list", "sg_head_in", "sg_take", "platform_status"}
    assert ("Shot", "sg_fp_test_checkbox") in report["dropped_fields"]
    assert ("Shot", "shot_sg_lineage_shots") in report["dropped_fields"]


def test_drops_enabled_custom_entities_and_custom_connections():
    schema, entities, report = clean_schema(*site(), UPSTREAM)
    for gone in ("CustomEntity09", "CustomEntity09_sg_photos_Connection", "Asset_sg_vendor_groups_Connection"):
        assert gone not in schema and gone not in entities
        assert gone in report["dropped_entities"]


def test_keeps_disabled_custom_entities():
    schema, entities, _ = clean_schema(*site(), UPSTREAM)
    assert "CustomEntity12" in schema and entities["CustomEntity12"]["visible"]["value"] is False


def test_prunes_valid_types_pointing_at_dropped_entities():
    schema, _, _ = clean_schema(*site(), UPSTREAM)
    assert schema["Shot"]["sg_take"]["properties"]["valid_types"]["value"] == ["Asset"]


def test_does_not_mutate_inputs():
    s, e = site()
    clean_schema(s, e, UPSTREAM)
    assert "sg_fp_test_checkbox" in s["Shot"] and "CustomEntity09" in e
