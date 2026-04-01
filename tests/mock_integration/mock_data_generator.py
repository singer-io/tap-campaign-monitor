"""Generic mock data generator for Singer tap integration tests.

Reads JSON schema files and generates mock API response data with
deterministic, type-conformant values.  Reusable across any tap —
only needs access to the schema directory.
"""
import copy
import json
import os
from datetime import datetime, timedelta


class MockDataGenerator:
    """Generates mock records from JSON schema files.

    Usage::

        gen = MockDataGenerator('/path/to/tap_foo/schemas')
        record = gen.generate_record('campaigns', seed=0)
        records = gen.generate_records('campaigns', count=3)
        response = gen.wrap_paginated(records, page=1, total_pages=2)
    """

    BASE_DATE = datetime(2024, 6, 15, 10, 0, 0)

    def __init__(self, schemas_dir):
        self.schemas_dir = schemas_dir
        self._schema_cache = {}

    # -------------------------------------------------------------- #
    #  Schema loading
    # -------------------------------------------------------------- #

    def load_schema(self, stream_name):
        """Load and cache a JSON schema file for *stream_name*."""
        if stream_name not in self._schema_cache:
            path = os.path.join(self.schemas_dir, f'{stream_name}.json')
            with open(path) as f:
                self._schema_cache[stream_name] = json.load(f)
        return self._schema_cache[stream_name]

    # -------------------------------------------------------------- #
    #  Value generation
    # -------------------------------------------------------------- #

    @staticmethod
    def resolve_type(type_spec):
        """Return the first non-null type from a JSON-Schema *type* field."""
        if isinstance(type_spec, list):
            for t in type_spec:
                if t != 'null':
                    return t
            return 'string'
        return type_spec

    @classmethod
    def generate_value(cls, field_name, field_schema, seed=0):
        """Return a deterministic value that conforms to *field_schema*."""
        type_str = cls.resolve_type(field_schema.get('type', 'string'))
        fmt = field_schema.get('format')

        if fmt == 'date-time':
            dt = cls.BASE_DATE + timedelta(days=seed)
            return dt.strftime('%Y-%m-%d %H:%M:%S')

        if type_str == 'string':
            return f"mock-{field_name.lower()}-{seed}"
        if type_str == 'number':
            return round(42.5 + seed * 1.1, 2)
        if type_str == 'integer':
            return 100 + seed
        if type_str == 'boolean':
            return seed % 2 == 0
        if type_str == 'array':
            return []
        if type_str == 'object':
            return {}
        return f"mock-{seed}"

    # -------------------------------------------------------------- #
    #  Record generation
    # -------------------------------------------------------------- #

    def generate_record(self, stream_name, seed=0, overrides=None,
                        exclude_fields=None):
        """Generate one mock record for *stream_name* from its schema.

        Parameters
        ----------
        stream_name : str
            Must match a ``<stream_name>.json`` file in *schemas_dir*.
        seed : int
            Deterministic seed so the same call always produces the
            same values.
        overrides : dict, optional
            Field values to force (applied after generation).
        exclude_fields : set, optional
            Fields to omit from the record (e.g. parent-ID fields that
            get injected by the stream class at sync time).
        """
        schema = self.load_schema(stream_name)
        record = {}
        exclude = exclude_fields or set()
        for field_name, field_schema in schema.get('properties', {}).items():
            if field_name in exclude:
                continue
            record[field_name] = self.generate_value(
                field_name, field_schema, seed)
        if overrides:
            record.update(overrides)
        return record

    def generate_records(self, stream_name, count=1, base_seed=0,
                         overrides=None, exclude_fields=None):
        """Generate *count* mock records with incrementing seeds."""
        return [
            self.generate_record(stream_name, seed=base_seed + i,
                                 overrides=overrides,
                                 exclude_fields=exclude_fields)
            for i in range(count)
        ]

    # -------------------------------------------------------------- #
    #  Response wrappers
    # -------------------------------------------------------------- #

    @staticmethod
    def wrap_paginated(records, page=1, total_pages=1, page_size=1000,
                       ordered_by='date', order_direction='asc'):
        """Wrap *records* in a paginated API response envelope.

        Matches the format used by Campaign Monitor (and similar APIs)::

            {Results: [...], NumberOfPages: N, PageNumber: P, ...}
        """
        return {
            "Results": records,
            "ResultsOrderedBy": ordered_by,
            "OrderDirection": order_direction,
            "PageNumber": page,
            "PageSize": page_size,
            "RecordsOnThisPage": len(records),
            "TotalNumberOfRecords": len(records) * total_pages,
            "NumberOfPages": total_pages,
        }
