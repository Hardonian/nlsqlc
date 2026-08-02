# SQLite schema importer

`tools/sqlite_schema_import.py` uses only Python's standard-library `sqlite3` module and opens the database read-only.

```sh
python3 tools/sqlite_schema_import.py app.db app.nlschema
./nlsqlc validate-ir --ir query.nlir --schema app.nlschema --policy policy.nlpolicy
```

The importer emits the native trusted format with public-schema mapping, table/column metadata, primary-key and not-null flags, tenant-column markers, and foreign-key relationships. SQLite internal tables are excluded. Unsupported or unsafe identifiers fail closed. The generated file still requires an explicit `.nlpolicy`; schema import never grants access by itself.
