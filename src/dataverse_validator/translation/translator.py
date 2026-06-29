#!/usr/bin/env python3
"""
translator.py

Core translation engine: Dataverse native API JSON → DataCite XML (kernel-4).

This file contains no metadata-block-specific logic. All field mappings live in
YAML files under blocks/. To add support for a new Dataverse metadata block,
write blocks/<block_name>.yaml (and add handler functions to handlers.py if needed).
Do not modify this file for per-block work.

USAGE
-----
    python3 translator.py <input.json> [output.xml]

    If no output path is given, the XML is printed to stdout.
    If no input path is given, it defaults to output.json.
"""

import json
import os
import sys
from xml.dom import minidom
from xml.etree import ElementTree as ET

import yaml

from .handlers import HANDLERS, TRANSFORMS

DATACITE_NS = "http://datacite.org/schema/kernel-4"
XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
SCHEMA_LOCATION = (
    "http://datacite.org/schema/kernel-4 "
    "http://schema.datacite.org/meta/kernel-4.5/metadata.xsd"
)

BLOCKS_DIR = os.path.join(os.path.dirname(__file__), "blocks")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_yaml(block_name):
    path = os.path.join(BLOCKS_DIR, f"{block_name}.yaml")
    with open(path) as f:
        return yaml.safe_load(f)


def _get_field(fields, type_name):
    """Find a field object by typeName in a Dataverse fields list."""
    for f in fields:
        if f["typeName"] == type_name:
            return f
    return None


def _resolve_parent(root, target_path):
    """
    Walk a slash-delimited target path, creating intermediate XML elements as
    needed. Returns (parent_element, leaf_tag_name).

    Example: "creators/creator" → creates <creators> if absent, returns
    (<creators_element>, "creator").

    The leaf element itself is left for the caller (or handler) to create.
    """
    parts = target_path.split("/")
    current = root
    for part in parts[:-1]:
        tag = f"{{{DATACITE_NS}}}{part}"
        existing = current.find(tag)
        if existing is None:
            existing = ET.SubElement(current, tag)
        current = existing
    return current, parts[-1]


# ---------------------------------------------------------------------------
# Mapping dispatcher
# ---------------------------------------------------------------------------

def _apply_mapping(mapping, context, root):
    """
    Apply one YAML mapping entry to the XML tree.

    context keys:
      "dataset"  — the root ds dict  (data["data"])
      "version"  — the latestVersion dict
      "fields"   — list of field objects for the current metadata block
                   (empty list for dataset.yaml mappings)
    """
    source = mapping["source"]
    target = mapping["target"]
    from_ctx = mapping.get("from", "fields")
    transform_name = mapping.get("transform")
    handler_name = mapping.get("handler")
    mapping_type = mapping.get("type", "primitive")
    attribs = mapping.get("attributes", {})

    parent_el, leaf_tag = _resolve_parent(root, target)

    # ---- Handler path -------------------------------------------------------
    # The handler receives the parent element and creates the target element(s)
    # itself. For block-level handlers (e.g. personal_name_entity), we first
    # fetch the field value from the fields list and pass it as `values`.
    # For dataset-level handlers (e.g. doi_identifier), values is None and the
    # handler reads from context directly.
    if handler_name:
        values = None
        if from_ctx == "fields":
            field = _get_field(context.get("fields", []), source)
            if field is None:
                return  # field absent in this dataset — skip
            values = field["value"]
        handler_fn = HANDLERS[handler_name]
        handler_config = mapping.get("handler_config", {})
        handler_fn(values, parent_el, handler_config, DATACITE_NS, context)
        return

    # ---- Non-handler path: look up the raw value ----------------------------
    if from_ctx == "dataset":
        raw_value = context["dataset"].get(source, mapping.get("default"))
    elif from_ctx == "version":
        raw_value = context["version"].get(source, mapping.get("default"))
    else:
        # Default: look up in the current block's fields list
        field = _get_field(context.get("fields", []), source)
        if field is None:
            return
        raw_value = field["value"]

    if raw_value is None:
        return

    # Apply optional transform
    if transform_name:
        raw_value = TRANSFORMS[transform_name](raw_value)
        if raw_value is None:
            return

    leaf_full_tag = f"{{{DATACITE_NS}}}{leaf_tag}"

    # ---- vocab_list: each string in the list becomes its own element --------
    if mapping_type == "vocab_list":
        for item in raw_value:
            ET.SubElement(parent_el, leaf_full_tag).text = item

    # ---- compound_list: each compound object becomes one element ------------
    elif mapping_type == "compound_list":
        text_from = mapping.get("text_from")
        children_spec = mapping.get("children", [])
        for entry in raw_value:
            el = ET.SubElement(parent_el, leaf_full_tag, **attribs)
            if text_from:
                text = entry.get(text_from, {}).get("value", "")
                if text:
                    el.text = text
            for child in children_spec:
                subfield = child["subfield"]
                val = entry.get(subfield, {}).get("value")
                if val:
                    child_transform = child.get("transform")
                    if child_transform:
                        val = TRANSFORMS[child_transform](val)
                    ET.SubElement(el, f"{{{DATACITE_NS}}}{child['tag']}").text = val

    # ---- primitive: single value, single element ----------------------------
    else:
        el = ET.SubElement(parent_el, leaf_full_tag, **attribs)
        el.text = raw_value


# ---------------------------------------------------------------------------
# Main translation function
# ---------------------------------------------------------------------------

def translate(data: dict) -> ET.Element:
    """
    Build a DataCite XML element tree from a Dataverse native API JSON dict.

    Steps:
      1. Collect mappings from dataset.yaml and any block YAMLs that match
         metadata blocks present in the JSON.
      2. Sort all mappings by their `order` key to ensure correct DataCite
         element sequence regardless of which YAML file each mapping comes from.
      3. Apply each mapping in order.
    """
    ET.register_namespace("", DATACITE_NS)
    ET.register_namespace("xsi", XSI_NS)

    ds = data["data"]
    version = ds["latestVersion"]

    root = ET.Element(
        f"{{{DATACITE_NS}}}resource",
        {f"{{{XSI_NS}}}schemaLocation": SCHEMA_LOCATION},
    )

    base_context = {"dataset": ds, "version": version}

    # Collect all (mapping, context) pairs from every applicable YAML file.
    # dataset.yaml always runs. Block YAMLs run only when the block is present.
    all_entries = []

    dataset_config = _load_yaml("dataset")
    dataset_context = {**base_context, "fields": []}
    for m in dataset_config["mappings"]:
        all_entries.append((m, dataset_context))

    for block_name, block_data in version["metadataBlocks"].items():
        yaml_path = os.path.join(BLOCKS_DIR, f"{block_name}.yaml")
        if not os.path.exists(yaml_path):
            continue
        block_config = _load_yaml(block_name)
        block_context = {**base_context, "fields": block_data["fields"]}
        for m in block_config["mappings"]:
            all_entries.append((m, block_context))

    # Sort by `order` key to produce DataCite's required element sequence
    all_entries.sort(key=lambda pair: pair[0].get("order", 999))

    for mapping, context in all_entries:
        _apply_mapping(mapping, context, root)

    return root


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------

def pretty_print(root: ET.Element) -> str:
    """
    Serialise an XML element tree to an indented, UTF-8 declared string.
    Uses minidom for indentation since ElementTree's built-in serialiser
    produces a single unindented line.
    """
    raw = ET.tostring(root, encoding="unicode", xml_declaration=False)
    reparsed = minidom.parseString(f'<?xml version="1.0" encoding="UTF-8"?>{raw}')
    return reparsed.toprettyxml(indent="  ", encoding=None).replace(
        '<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8"?>'
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    in_path = sys.argv[1] if len(sys.argv) > 1 else "output.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else None

    with open(in_path) as f:
        data = json.load(f)

    root = translate(data)
    xml_str = pretty_print(root)

    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(xml_str)
        print(f"Written to {out_path}")
    else:
        print(xml_str)


if __name__ == "__main__":
    main()
