"""Setup: create the `pii` aspect type and attach it to columns of thelook_ecommerce.users.

Run once after copying the thelook_ecommerce tables into your project (see the
bq commands in the tutorial). Requires roles/dataplex.catalogEditor.
"""

from google.api_core import exceptions
from google.cloud import dataplex_v1
from google.protobuf import struct_pb2

PROJECT_ID = "example-project"

# BigQuery entries are cataloged in the dataset's region (US multi-region here).
USERS_ENTRY = (
    f"projects/{PROJECT_ID}/locations/us/entryGroups/@bigquery/entries/"
    f"bigquery.googleapis.com/projects/{PROJECT_ID}/datasets/thelook_ecommerce/tables/users"
)

# Column -> (pii_type, masked). The mix of masked values is intentional: the
# PII audit scenario then has a meaningful answer instead of returning everything.
PII_COLUMNS = {
    "email": ("EMAIL", False),
    "first_name": ("NAME", False),
    "last_name": ("NAME", False),
    "street_address": ("ADDRESS", False),
    "postal_code": ("ADDRESS", True),
    "age": ("DEMOGRAPHIC", True),
    "gender": ("DEMOGRAPHIC", True),
}


def create_pii_aspect_type() -> dataplex_v1.AspectType:
    with dataplex_v1.CatalogServiceClient() as client:
        aspect_type = dataplex_v1.AspectType(
            description="Marks a column as containing personally identifiable information.",
            metadata_template=dataplex_v1.AspectType.MetadataTemplate(
                name="pii",
                type_="record",
                record_fields=[
                    dataplex_v1.AspectType.MetadataTemplate(
                        name="pii_type",
                        type_="enum",
                        index=1,
                        annotations=dataplex_v1.AspectType.MetadataTemplate.Annotations(
                            display_name="PII type",
                            description="Category of personally identifiable information in this column.",
                        ),
                        constraints=dataplex_v1.AspectType.MetadataTemplate.Constraints(
                            required=True
                        ),
                        enum_values=[
                            dataplex_v1.AspectType.MetadataTemplate.EnumValue(name="EMAIL", index=1),
                            dataplex_v1.AspectType.MetadataTemplate.EnumValue(name="NAME", index=2),
                            dataplex_v1.AspectType.MetadataTemplate.EnumValue(name="ADDRESS", index=3),
                            dataplex_v1.AspectType.MetadataTemplate.EnumValue(name="PHONE_NUMBER", index=4),
                            dataplex_v1.AspectType.MetadataTemplate.EnumValue(name="DEMOGRAPHIC", index=5),
                            dataplex_v1.AspectType.MetadataTemplate.EnumValue(name="OTHER", index=6),
                        ],
                    ),
                    dataplex_v1.AspectType.MetadataTemplate(
                        name="masked",
                        type_="bool",
                        index=2,
                        annotations=dataplex_v1.AspectType.MetadataTemplate.Annotations(
                            display_name="Masked",
                            description="Whether this column is masked or de-identified downstream.",
                        ),
                    ),
                ],
            ),
        )
        # Created in the global location: searchable from anywhere, one less
        # flag to explain in the search examples.
        # Safe to re-run: if the aspect type already exists, return it as is.
        try:
            operation = client.create_aspect_type(
                parent=f"projects/{PROJECT_ID}/locations/global",
                aspect_type=aspect_type,
                aspect_type_id="pii",
            )
            return operation.result(timeout=60)
        except exceptions.AlreadyExists:
            return client.get_aspect_type(
                name=f"projects/{PROJECT_ID}/locations/global/aspectTypes/pii"
            )


def attach_pii_aspects() -> dataplex_v1.Entry:
    with dataplex_v1.CatalogServiceClient() as client:
        aspects = {}
        for column, (pii_type, masked) in PII_COLUMNS.items():
            # Column-level aspect keys use the format
            # <project>.<location>.<aspect_type_id>@Schema.<column>
            key = f"{PROJECT_ID}.global.pii@Schema.{column}"
            aspects[key] = dataplex_v1.Aspect(
                aspect_type=f"projects/{PROJECT_ID}/locations/global/aspectTypes/pii",
                data=struct_pb2.Struct(
                    fields={
                        "pii_type": struct_pb2.Value(string_value=pii_type),
                        "masked": struct_pb2.Value(bool_value=masked),
                    }
                ),
            )
        entry = dataplex_v1.Entry(name=USERS_ENTRY, aspects=aspects)
        return client.update_entry(
            entry=entry, update_mask={"paths": ["aspects"]}
        )


if __name__ == "__main__":
    aspect_type = create_pii_aspect_type()
    print(f"Created aspect type: {aspect_type.name}")
    entry = attach_pii_aspects()
    print(f"Attached PII aspects to: {entry.name}")
    for key in entry.aspects:
        print(f"  {key}")

# Expected output:
#
# Created aspect type: projects/example-project/locations/global/aspectTypes/pii
# Attached PII aspects to: projects/example-project/locations/us/entryGroups/@bigquery/entries/bigquery.googleapis.com/projects/example-project/datasets/thelook_ecommerce/tables/users
#   example-project.global.pii@Schema.email
#   example-project.global.pii@Schema.first_name
#   example-project.global.pii@Schema.last_name
#   example-project.global.pii@Schema.street_address
#   example-project.global.pii@Schema.postal_code
#   example-project.global.pii@Schema.age
#   example-project.global.pii@Schema.gender
