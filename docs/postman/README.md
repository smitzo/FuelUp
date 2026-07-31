# FuelUp API request collection

Import `FuelUp-Route-API.postman_collection.json` into Postman, its VS Code
extension, or another client supporting Collection v2.1.

The collection exercises the market-neutral v2 contract with the checked-in
India configuration:

1. A vehicle-aware route with a waypoint and declared units.
2. Validation of an impossible starting-fuel plus reserve combination.
3. Honest `insufficient_price_data` behaviour when no active catalogue exists.

Set `baseUrl` to `http://127.0.0.1:8000` locally or to the deployed Django API.
Before expecting a successful plan, synchronize the source registry and load an
active station snapshot plus accepted current observations as described in
[`../data-sources.md`](../data-sources.md).

The canonical field-level contract is [`../../openapi.yaml`](../../openapi.yaml).
