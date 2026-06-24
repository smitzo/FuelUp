# FuelUp API request collection

Import `FuelUp-Route-API.postman_collection.json` into Postman, the Postman VS
Code extension, or another client that supports Postman Collection v2.1.

The collection contains route requests only:

1. Successful Austin-to-Dallas route.
2. Immediate repeat to demonstrate `X-FuelUp-Cache: HIT`.
3. Los Angeles-to-New York route with multiple fuel stops.
4. Invalid request validation.
5. Unsupported non-U.S. locations.

Set the collection variable `baseUrl`:

```text
Local:  http://127.0.0.1:8000
Render: https://your-service.onrender.com
```

Start the local API before using the local URL:

```bash
source .venv/bin/activate
python manage.py runserver 127.0.0.1:8000
```

Each request includes Postman tests for its status, response contract, cache
headers, or fuel-plan rules.

For a field-by-field explanation of the JSON response, headers, route score,
backend execution flow, and OpenAPI keywords, read sections 4, 8, 13, and 14
of [`understanding.md`](../../understanding.md).
