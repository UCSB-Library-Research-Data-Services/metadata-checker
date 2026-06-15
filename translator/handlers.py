"""
handlers.py

Named transform functions and handler functions for the Dataverse → DataCite translator.

Transforms: simple string-to-string functions applied to a single field value.
            Referenced in YAML as `transform: <name>`.

Handlers:   Python functions for fields too complex to express in YAML config —
            name splitting, multi-element output, conditional logic, etc.
            Referenced in YAML as `handler: <name>`.

Both registries (TRANSFORMS, HANDLERS) are imported by translate.py.
To add a new transform or handler, write the function and add it to the
appropriate dict at the bottom of this file.
"""

import re
from xml.etree import ElementTree as ET


# ---------------------------------------------------------------------------
# Transforms
#
# Each entry is a callable: str | None → str | None.
# Returning None causes translate.py to skip writing the element entirely.
# ---------------------------------------------------------------------------

TRANSFORMS = {
    # "2026-04-16"              → "2026"
    # "2026-04-16T06:57:35Z"   → "2026"
    "year_only": lambda s: s[:4] if s else None,

    # "2026-04-16T06:57:35Z"   → "2026-04-16"
    "trim_datetime": lambda s: s[:10] if s else None,

    # "dataset"  → "Dataset"
    "capitalize": lambda s: s.capitalize() if s else None,
}


# ---------------------------------------------------------------------------
# Name-splitting utilities shared by personal_name_entity and other handlers
# ---------------------------------------------------------------------------

def _parse_name(full_name):
    """
    Split "Last, First" → (given, family).
    Fallback for names without a comma: split on the last space.
    Single-word names return (name, "").
    """
    if "," in full_name:
        family, _, given = full_name.partition(",")
        return given.strip(), family.strip()
    parts = full_name.strip().split()
    if len(parts) >= 2:
        return " ".join(parts[:-1]), parts[-1]
    return full_name, ""


def _is_personal_name(full_name):
    """
    Heuristic: "Uppercase-word, Uppercase-letter" pattern → Personal.
    Organisation names (e.g. "UCSB Library") do not match this pattern.
    """
    return bool(re.search(r"[A-Z][a-z]+,\s*[A-Z]", full_name))


# ---------------------------------------------------------------------------
# Handlers
#
# Signature: fn(values, parent_el, config, ns, context)
#
#   values      — field value from the JSON (list for compound/vocab fields,
#                 None for dataset-level handlers that read from context directly)
#   parent_el   — XML element to append into (the resolved parent from target path)
#   config      — handler_config dict from the YAML mapping (may be empty {})
#   ns          — DataCite namespace URI string
#   context     — dict with keys: "dataset" (ds root), "version" (latestVersion),
#                 "fields" (current block's field list)
# ---------------------------------------------------------------------------

def personal_name_entity(values, parent_el, config, ns, context):
    """
    Creates <creator> or <contributor> elements from a compound author/contact field.

    Handles "Last, First" name splitting, Personal/Organizational nameType inference,
    and optional <affiliation>.

    handler_config keys:
      name_field:        subfield holding the full name (e.g. "authorName")
      affiliation_field: optional subfield for affiliation (e.g. "authorAffiliation")
      datacite_role:     "creator" or "contributor"
      contributor_type:  required when datacite_role is "contributor" (e.g. "ContactPerson")
    """
    name_field = config["name_field"]
    affiliation_field = config.get("affiliation_field")
    role = config["datacite_role"]
    contributor_type = config.get("contributor_type")

    for entry in values:
        full = entry[name_field]["value"]
        given, family = _parse_name(full)
        name_type = "Personal" if _is_personal_name(full) else "Organizational"

        attribs = {}
        if contributor_type:
            attribs["contributorType"] = contributor_type
        entity_el = ET.SubElement(parent_el, f"{{{ns}}}{role}", **attribs)

        name_tag = "creatorName" if role == "creator" else "contributorName"
        name_el = ET.SubElement(entity_el, f"{{{ns}}}{name_tag}", nameType=name_type)
        name_el.text = full

        if given:
            ET.SubElement(entity_el, f"{{{ns}}}givenName").text = given
        if family:
            ET.SubElement(entity_el, f"{{{ns}}}familyName").text = family

        if affiliation_field:
            aff = entry.get(affiliation_field, {}).get("value")
            if aff:
                ET.SubElement(entity_el, f"{{{ns}}}affiliation").text = aff


def doi_identifier(values, parent_el, config, ns, context):
    """
    Writes <identifier identifierType="DOI"> by joining ds.authority and ds.identifier.
    Reads from context["dataset"] directly — `values` is unused.
    """
    ds = context["dataset"]
    doi = f"{ds['authority']}/{ds['identifier']}"
    ET.SubElement(parent_el, f"{{{ns}}}identifier", identifierType="DOI").text = doi


def publication_year(values, parent_el, config, ns, context):
    """
    Writes <publicationYear> from the dataset- or version-level publicationDate.
    Tries ds.publicationDate first, falls back to version.publicationDate.
    """
    ds = context["dataset"]
    ver = context["version"]
    date = ds.get("publicationDate") or ver.get("publicationDate")
    if date:
        ET.SubElement(parent_el, f"{{{ns}}}publicationYear").text = date[:4]


def resource_type_element(values, parent_el, config, ns, context):
    """
    Writes <resourceType resourceTypeGeneral="Dataset"/>.
    The element has no text content — only the resourceTypeGeneral attribute.
    Capitalizes ds.datasetType (e.g. "dataset" → "Dataset").
    """
    ds = context["dataset"]
    resource_type = ds.get("datasetType", "dataset").capitalize()
    ET.SubElement(parent_el, f"{{{ns}}}resourceType", resourceTypeGeneral=resource_type)


def dataset_dates(values, parent_el, config, ns, context):
    """
    Writes <dates> with Available and Updated children.

    Available: version.publicationDate, falling back to version.citationDate.
    Updated:   version.lastUpdateTime, trimmed to YYYY-MM-DD.

    parent_el is root; this handler creates the <dates> container itself.
    """
    ver = context["version"]
    available = ver.get("publicationDate") or ver.get("citationDate")
    updated_raw = ver.get("lastUpdateTime")

    if not available and not updated_raw:
        return

    dates_el = ET.SubElement(parent_el, f"{{{ns}}}dates")
    if available:
        ET.SubElement(dates_el, f"{{{ns}}}date", dateType="Available").text = available
    if updated_raw:
        ET.SubElement(dates_el, f"{{{ns}}}date", dateType="Updated").text = updated_raw[:10]


def dataset_version(values, parent_el, config, ns, context):
    """
    Writes <version>major.minor</version>.
    Skipped for draft datasets, which have no versionNumber yet.
    """
    ver = context["version"]
    major = ver.get("versionNumber")
    minor = ver.get("versionMinorNumber")
    if major is not None and minor is not None:
        ET.SubElement(parent_el, f"{{{ns}}}version").text = f"{major}.{minor}"


def file_sizes(values, parent_el, config, ns, context):
    """
    Writes <sizes><size>N</size></sizes> for the total byte count of all files.
    Skipped entirely if no files are present.
    parent_el is root; this handler creates the <sizes> container itself.
    """
    files = context["version"].get("files", [])
    total = sum(f["dataFile"].get("filesize", 0) for f in files)
    if total:
        sizes_el = ET.SubElement(parent_el, f"{{{ns}}}sizes")
        ET.SubElement(sizes_el, f"{{{ns}}}size").text = str(total)


def file_formats(values, parent_el, config, ns, context):
    """
    Writes <formats><format>mime/type</format>...</formats>, one entry per unique
    content type, in first-seen order.
    parent_el is root; this handler creates the <formats> container itself.
    """
    files = context["version"].get("files", [])
    seen = list(dict.fromkeys(
        f["dataFile"]["contentType"]
        for f in files
        if f["dataFile"].get("contentType")
    ))
    if seen:
        formats_el = ET.SubElement(parent_el, f"{{{ns}}}formats")
        for fmt in seen:
            ET.SubElement(formats_el, f"{{{ns}}}format").text = fmt


def rights_list(values, parent_el, config, ns, context):
    """
    Writes <rightsList> with:
      - An open-access URI entry if any file in the dataset is unrestricted.
      - The dataset licence from version.license (name + URI).
    parent_el is root; this handler creates the <rightsList> container itself.
    """
    OPEN_ACCESS_URI = "info:eu-repo/semantics/openAccess"
    ver = context["version"]
    files = ver.get("files", [])

    any_open = any(not f.get("restricted", True) for f in files)
    license_info = ver.get("license")

    if not any_open and not license_info:
        return

    rights_el = ET.SubElement(parent_el, f"{{{ns}}}rightsList")
    if any_open:
        ET.SubElement(rights_el, f"{{{ns}}}rights", rightsURI=OPEN_ACCESS_URI)
    if license_info:
        el = ET.SubElement(
            rights_el, f"{{{ns}}}rights",
            rightsURI=license_info.get("uri", ""),
        )
        el.text = license_info.get("name", "")


# ---------------------------------------------------------------------------
# Registries — translate.py looks up by name from these dicts
# ---------------------------------------------------------------------------

HANDLERS = {
    "personal_name_entity": personal_name_entity,
    "doi_identifier": doi_identifier,
    "publication_year": publication_year,
    "resource_type_element": resource_type_element,
    "dataset_dates": dataset_dates,
    "dataset_version": dataset_version,
    "file_sizes": file_sizes,
    "file_formats": file_formats,
    "rights_list": rights_list,
}
