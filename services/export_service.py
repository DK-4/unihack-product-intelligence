"""
Export service: maps our internal ProductState/record onto the official
UniHack "Expected Output - Delivery Format" schema (252 fixed headers).

Per the submission rules, headers must never be renamed, removed, or
reordered -- only their values are populated. Unmapped/unknown fields are
left blank rather than guessed.
"""
from __future__ import annotations

import io
import os

import pandas as pd

EXPECTED_OUTPUT_HEADERS = [
    'MFR URL',
    'Ref URL 1',
    'Ref URL 2',
    'Ref URL 3',
    'Ref URL 4',
    'Ref URL 5',
    'PART_NUMBER',
    'Dept',
    'Class',
    'Fine',
    'SKU - MY_PART_NUMBER',
    'Mfg_Part_Num',
    'Part_Desc',
    'E1_Brand',
    'Unilog_Brand',
    'DIB_Brand',
    'Part_Manuf',
    'MANUFACTURER_NAME',
    'BRAND_NAME',
    'TRADE_NAME',
    'MANUFACTURER_PART_NUMBER',
    'ALTERNATE_PART_NUMBER',
    'Classpath',
    'MOBILE_DESC',
    'INVOICE_DESC',
    'SHORT_DESC',
    'LONG_DESC1',
    'RETAIL_DESC',
    'MARKETING_DESCRIPTION',
    'ITEM_FEATURES_1',
    'ITEM_FEATURES_2',
    'ITEM_FEATURES_3',
    'ITEM_FEATURES_4',
    'ITEM_FEATURES_5',
    'ITEM_FEATURES_6',
    'ITEM_FEATURES_7',
    'ITEM_FEATURES_8',
    'ITEM_FEATURES_9',
    'ITEM_FEATURES_10',
    'ITEM_FEATURES_11',
    'ITEM_FEATURES_12',
    'ITEM_FEATURES_13',
    'ITEM_FEATURES_14',
    'ITEM_FEATURES_15',
    'ITEM_FEATURES_16',
    'ITEM_FEATURES_17',
    'ITEM_FEATURES_18',
    'ITEM_FEATURES_19',
    'ITEM_FEATURES_20',
    'With',
    'Standard/Approvals',
    'Prop 65',
    'Application',
    'Includes',
    'Product Name',
    'ATTRIBUTE_LABEL 1',
    'ATTRIBUTE_VALUE 1',
    'ATTRIBUTE_UOM 1',
    'ATTRIBUTE_LABEL 2',
    'ATTRIBUTE_VALUE 2',
    'ATTRIBUTE_UOM 2',
    'ATTRIBUTE_LABEL 3',
    'ATTRIBUTE_VALUE 3',
    'ATTRIBUTE_UOM 3',
    'ATTRIBUTE_LABEL 4',
    'ATTRIBUTE_VALUE 4',
    'ATTRIBUTE_UOM 4',
    'ATTRIBUTE_LABEL 5',
    'ATTRIBUTE_VALUE 5',
    'ATTRIBUTE_UOM 5',
    'ATTRIBUTE_LABEL 6',
    'ATTRIBUTE_VALUE 6',
    'ATTRIBUTE_UOM 6',
    'ATTRIBUTE_LABEL 7',
    'ATTRIBUTE_VALUE 7',
    'ATTRIBUTE_UOM 7',
    'ATTRIBUTE_LABEL 8',
    'ATTRIBUTE_VALUE 8',
    'ATTRIBUTE_UOM 8',
    'ATTRIBUTE_LABEL 9',
    'ATTRIBUTE_VALUE 9',
    'ATTRIBUTE_UOM 9',
    'ATTRIBUTE_LABEL 10',
    'ATTRIBUTE_VALUE 10',
    'ATTRIBUTE_UOM 10',
    'ATTRIBUTE_LABEL 11',
    'ATTRIBUTE_VALUE 11',
    'ATTRIBUTE_UOM 11',
    'ATTRIBUTE_LABEL 12',
    'ATTRIBUTE_VALUE 12',
    'ATTRIBUTE_UOM 12',
    'ATTRIBUTE_LABEL 13',
    'ATTRIBUTE_VALUE 13',
    'ATTRIBUTE_UOM 13',
    'ATTRIBUTE_LABEL 14',
    'ATTRIBUTE_VALUE 14',
    'ATTRIBUTE_UOM 14',
    'ATTRIBUTE_LABEL 15',
    'ATTRIBUTE_VALUE 15',
    'ATTRIBUTE_UOM 15',
    'ATTRIBUTE_LABEL 16',
    'ATTRIBUTE_VALUE 16',
    'ATTRIBUTE_UOM 16',
    'ATTRIBUTE_LABEL 17',
    'ATTRIBUTE_VALUE 17',
    'ATTRIBUTE_UOM 17',
    'ATTRIBUTE_LABEL 18',
    'ATTRIBUTE_VALUE 18',
    'ATTRIBUTE_UOM 18',
    'ATTRIBUTE_LABEL 19',
    'ATTRIBUTE_VALUE 19',
    'ATTRIBUTE_UOM 19',
    'ATTRIBUTE_LABEL 20',
    'ATTRIBUTE_VALUE 20',
    'ATTRIBUTE_UOM 20',
    'ATTRIBUTE_LABEL 21',
    'ATTRIBUTE_VALUE 21',
    'ATTRIBUTE_UOM 21',
    'ATTRIBUTE_LABEL 22',
    'ATTRIBUTE_VALUE 22',
    'ATTRIBUTE_UOM 22',
    'ATTRIBUTE_LABEL 23',
    'ATTRIBUTE_VALUE 23',
    'ATTRIBUTE_UOM 23',
    'ATTRIBUTE_LABEL 24',
    'ATTRIBUTE_VALUE 24',
    'ATTRIBUTE_UOM 24',
    'ATTRIBUTE_LABEL 25',
    'ATTRIBUTE_VALUE 25',
    'ATTRIBUTE_UOM 25',
    'ATTRIBUTE_LABEL 26',
    'ATTRIBUTE_VALUE 26',
    'ATTRIBUTE_UOM 26',
    'ATTRIBUTE_LABEL 27',
    'ATTRIBUTE_VALUE 27',
    'ATTRIBUTE_UOM 27',
    'ATTRIBUTE_LABEL 28',
    'ATTRIBUTE_VALUE 28',
    'ATTRIBUTE_UOM 28',
    'ATTRIBUTE_LABEL 29',
    'ATTRIBUTE_VALUE 29',
    'ATTRIBUTE_UOM 29',
    'ATTRIBUTE_LABEL 30',
    'ATTRIBUTE_VALUE 30',
    'ATTRIBUTE_UOM 30',
    'ATTRIBUTE_LABEL 31',
    'ATTRIBUTE_VALUE 31',
    'ATTRIBUTE_UOM 31',
    'ATTRIBUTE_LABEL 32',
    'ATTRIBUTE_VALUE 32',
    'ATTRIBUTE_UOM 32',
    'ATTRIBUTE_LABEL 33',
    'ATTRIBUTE_VALUE 33',
    'ATTRIBUTE_UOM 33',
    'ATTRIBUTE_LABEL 34',
    'ATTRIBUTE_VALUE 34',
    'ATTRIBUTE_UOM 34',
    'ATTRIBUTE_LABEL 35',
    'ATTRIBUTE_VALUE 35',
    'ATTRIBUTE_UOM 35',
    'ATTRIBUTE_LABEL 36',
    'ATTRIBUTE_VALUE 36',
    'ATTRIBUTE_UOM 36',
    'ATTRIBUTE_LABEL 37',
    'ATTRIBUTE_VALUE 37',
    'ATTRIBUTE_UOM 37',
    'ATTRIBUTE_LABEL 38',
    'ATTRIBUTE_VALUE 38',
    'ATTRIBUTE_UOM 38',
    'ATTRIBUTE_LABEL 39',
    'ATTRIBUTE_VALUE 39',
    'ATTRIBUTE_UOM 39',
    'ATTRIBUTE_LABEL 40',
    'ATTRIBUTE_VALUE 40',
    'ATTRIBUTE_UOM 40',
    'ATTRIBUTE_LABEL 41',
    'ATTRIBUTE_VALUE 41',
    'ATTRIBUTE_UOM 41',
    'ATTRIBUTE_LABEL 42',
    'ATTRIBUTE_VALUE 42',
    'ATTRIBUTE_UOM 42',
    'ATTRIBUTE_LABEL 43',
    'ATTRIBUTE_VALUE 43',
    'ATTRIBUTE_UOM 43',
    'ATTRIBUTE_LABEL 44',
    'ATTRIBUTE_VALUE 44',
    'ATTRIBUTE_UOM 44',
    'ATTRIBUTE_LABEL 45',
    'ATTRIBUTE_VALUE 45',
    'ATTRIBUTE_UOM 45',
    'ATTRIBUTE_LABEL 46',
    'ATTRIBUTE_VALUE 46',
    'ATTRIBUTE_UOM 46',
    'ATTRIBUTE_LABEL 47',
    'ATTRIBUTE_VALUE 47',
    'ATTRIBUTE_UOM 47',
    'ATTRIBUTE_LABEL 48',
    'ATTRIBUTE_VALUE 48',
    'ATTRIBUTE_UOM 48',
    'ATTRIBUTE_LABEL 49',
    'ATTRIBUTE_VALUE 49',
    'ATTRIBUTE_UOM 49',
    'ATTRIBUTE_LABEL 50',
    'ATTRIBUTE_VALUE 50',
    'ATTRIBUTE_UOM 50',
    'UPC',
    'EAN',
    'GTIN',
    'UNSPSC',
    'Warranty',
    'List Price',
    'Selling Qty',
    'Selling UOM',
    'Standard Packaging Information',
    'LENGTH',
    'LENGTH_UOM',
    'HEIGHT',
    'HEIGHT_UOM',
    'WIDTH',
    'WIDTH_UOM',
    'WEIGHT',
    'WEIGHT_UOM',
    'VOLUME',
    'VOLUME_UOM',
    'Product Image',
    'Alternate Image 1',
    'Alternate Image 2',
    'Alternate Image 3',
    'Alternate Image 4',
    'SDS',
    'SDS_1',
    'Warranty Information',
    'Catalog',
    'Specification Sheet',
    'Instruction/Installation Manual',
    'Service Manual',
    'Owners/User Manual',
    'Line Drawing',
    'MTR',
    'RoHS',
    'Full Engineering Drawing',
    'Energy Star Guide',
    'Technical Bulletin',
    'Submittal',
    'Compatibility Chart',
    'Size Chart',
    'Product Label/Insert',
    'Video Link',
    'Video Link 1',
    'Country Of Origin',
    'Discontinued',
    'Actual Image (Yes/No)',
]

assert len(EXPECTED_OUTPUT_HEADERS) == 252


def build_expected_output_row(record: dict, pdf_path: str | None = None, image_path: str | None = None) -> dict:
    """Map our final product record (from ProductState.to_final_json()) onto
    the official 252-column schema. Returns a dict of {header: value}.
    """
    row = {h: "" for h in EXPECTED_OUTPUT_HEADERS}

    part_number = (record.get("attributes", {}).get("part_number") or {}).get("value", "")
    brand = record.get("manufacturer") or ""
    category = record.get("category") or ""
    subcategory = record.get("subcategory") or ""
    product_name = record.get("product_name") or ""
    description_obj = record.get("description") or {}
    enriched_description = description_obj.get("value", "") if description_obj else ""

    row["PART_NUMBER"] = part_number
    row["SKU - MY_PART_NUMBER"] = part_number
    row["Mfg_Part_Num"] = part_number
    row["MANUFACTURER_PART_NUMBER"] = part_number
    row["MANUFACTURER_NAME"] = brand
    row["BRAND_NAME"] = brand
    row["Part_Manuf"] = brand
    row["Dept"] = category
    row["Class"] = subcategory
    row["Classpath"] = " > ".join([p for p in [category, subcategory] if p and p != "unknown"])
    row["Product Name"] = product_name
    row["Part_Desc"] = product_name
    row["SHORT_DESC"] = product_name
    row["LONG_DESC1"] = enriched_description
    row["MARKETING_DESCRIPTION"] = enriched_description
    row["RETAIL_DESC"] = enriched_description

    # Applications -> ITEM_FEATURES_1..20 and the single "Application" column
    apps = [a.get("value", "") for a in record.get("applications", {}).values()]
    row["Application"] = ", ".join(apps)
    for i, app in enumerate(apps[:20], start=1):
        row[f"ITEM_FEATURES_{i}"] = app

    # Attributes -> ATTRIBUTE_LABEL/VALUE/UOM 1..50
    attrs = {k: v for k, v in record.get("attributes", {}).items() if k not in ("part_number", "brand")}
    for i, (name, attr) in enumerate(list(attrs.items())[:50], start=1):
        row[f"ATTRIBUTE_LABEL {i}"] = name.replace("_", " ").title()
        row[f"ATTRIBUTE_VALUE {i}"] = attr.get("value", "")
        row[f"ATTRIBUTE_UOM {i}"] = attr.get("unit") or ""

    # Files
    if pdf_path:
        row["Specification Sheet"] = os.path.basename(pdf_path)
    if image_path:
        row["Product Image"] = os.path.basename(image_path)
        row["Actual Image (Yes/No)"] = "Yes"
    else:
        row["Actual Image (Yes/No)"] = "No"

    return row


def row_to_dataframe(row: dict) -> pd.DataFrame:
    return pd.DataFrame([row], columns=EXPECTED_OUTPUT_HEADERS)


def to_csv_bytes(row: dict) -> bytes:
    df = row_to_dataframe(row)
    return df.to_csv(index=False).encode("utf-8")


def to_xlsx_bytes(row: dict) -> bytes:
    df = row_to_dataframe(row)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Expected Output")
    return buffer.getvalue()
