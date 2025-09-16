Backup DB:
```
uv run manage.py dumpdata -o "mai_inventory_$(date +%Y%m%d_%H%M%S).json.gz"
```

Load DB
```
gunzip <file_name>
uv run manage.py loaddata -e auth.Permission -e contenttypes <file_name>.json
```