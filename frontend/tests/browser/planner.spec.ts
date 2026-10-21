import { expect, test } from "@playwright/test";

// Explicitly synthetic browser contract fixture; never bundled into the product.
const now = "2026-10-26T08:00:00Z";
const plan = {
  api_version: "v2",
  market: { country_name: "India", country_code: "in", code: "IN", currency_code: "INR", distance_unit: "km", volume_unit: "litre", efficiency_unit: "km/litre" },
  start: { query: "Ahmedabad", display_name: "Ahmedabad, Gujarat", latitude: 23, longitude: 72.5 },
  finish: { query: "Vadodara", display_name: "Vadodara, Gujarat", latitude: 22.3, longitude: 73.2 },
  waypoints: [],
  route: { distance: 160, duration_hours: 2.5, geojson: { type: "FeatureCollection", features: [{ type: "Feature", geometry: { type: "LineString", coordinates: [[72.5, 23], [73.2, 22.3]] }, properties: { kind: "route" } }] } },
  vehicle: { fuel_type: "petrol", fuel_grade: null, tank_capacity: 35, efficiency: 18, starting_fuel: 8, reserve_fuel: 3, maximum_range: 576, maximum_station_detour: 5 },
  fuel_plan: { starting_fuel: 8, reserve_fuel: 3, total_consumed_volume: 8.89, purchased_volume: 1, purchase_cost: 101, arrival_fuel: 0.11, currency: "INR", stops: [{ sequence: 1, station_id: "test-pump", name: "Browser test pump", address: "Test address", city: "Anand", state: "Gujarat", latitude: 22.56, longitude: 72.96, route_distance: 80, distance_to_route: 0.2, unit_price: 101, price: { label: "reference", geographic_precision: "city", confidence: "low", as_of: now, expires_at: "2026-10-27T08:00:00Z", observation_ids: ["test-1"], resolver_version: "test" }, fuel_on_arrival: 3.56, volume: 1, cost: 101 }] },
  comparisons: [],
  data_quality: { station_snapshot: "synthetic-browser-fixture", station_snapshot_generated_at: now, observation_watermark: 1, required_stop_quotes: 1, resolved_stop_quotes: 1, price_coverage_percent: 100, label_counts: { reference: 1 }, confidence_counts: { low: 1 }, oldest_price_as_of: now, warning: "City reference; detours estimated." },
  metadata: { strategy: "balanced", price_quality_policy: "best_available", route_alternatives_evaluated: 1, feasible_route_alternatives: 1, selected_alternative: 1, selection_score: 101, routing_provider: "test", geocoding_provider: "test", detour_validation: "estimated", station_attribution: "Test fixture" },
};

test.beforeEach(async ({ page }) => {
  // Contract fixtures exercise the product without contacting public services.
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    return url.hostname === "127.0.0.1" ? route.continue() : route.abort();
  });
  await page.goto("/");
});

test("trip results show price evidence and offer downloads without loading tiles", async ({ page }) => {
  let requests = 0;
  await page.route("**/api/route", async (route) => {
    requests += 1;
    expect(route.request().postDataJSON().vehicle.fuel_type).toBe("petrol");
    await new Promise((resolve) => setTimeout(resolve, 500));
    await route.fulfill({ json: plan });
  });
  await page.getByRole("button", { name: "Plan my route" }).click();
  await expect(page.locator(".loading-truck")).toBeVisible();
  await expect(page.getByText("Estimated top-up spend")).toBeVisible();
  await expect(page.getByText("Browser test pump")).toBeVisible();
  await expect(page.getByText("Valid until", { exact: false })).toBeVisible();
  await expect(page.locator(".leaflet-container")).toHaveCount(0);
  await expect(page.getByRole("link", { name: "Navigate to this stop" })).toHaveAttribute("href", /destination=22.56%2C72.96/);
  const downloaded = page.waitForEvent("download");
  await page.getByRole("button", { name: "Save trip JSON" }).click();
  expect((await downloaded).suggestedFilename()).toBe("fuelup-trip.json");
  expect(requests).toBe(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});

test("vehicle reserves validate before network and saved values can be restored", async ({ page }) => {
  let requested = false;
  await page.route("**/api/route", (route) => { requested = true; return route.abort(); });
  await page.locator("summary").filter({ hasText: "Vehicle & fuel" }).click();
  await page.getByLabel("Starting fuel (L)").fill("34");
  await page.getByRole("button", { name: "Plan my route" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "cannot exceed" })).toBeVisible();
  expect(requested).toBe(false);
  await page.getByLabel("Starting fuel (L)").fill("8");
  await page.getByRole("button", { name: "Save vehicle", exact: true }).click();
  await page.getByLabel("Mileage (km/L)").fill("20");
  await page.getByRole("button", { name: "Use saved vehicle" }).click();
  await expect(page.getByLabel("Mileage (km/L)")).toHaveValue("18");
  await page.getByRole("button", { name: "Forget saved vehicle" }).click();
  await expect(page.getByRole("status")).toContainText("removed");
});

test("cancel keeps the form usable and coverage failures have useful copy", async ({ page }) => {
  await page.route("**/api/route", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 1200));
    await route.fulfill({ status: 422, json: { error: { code: "insufficient_price_data", message: "No prices" } } }).catch(() => {});
  });
  await page.getByRole("button", { name: "Plan my route" }).click();
  await page.getByRole("button", { name: "Cancel planning" }).click();
  await expect(page.getByRole("button", { name: "Plan my route" })).toBeEnabled();
  await page.getByRole("button", { name: "Plan my route" }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Price coverage is not ready" })).toBeVisible();
  await expect(page.locator(".results-focus")).toBeFocused();
});

test("keyboard navigation reaches the planner and results without a map", async ({ page }) => {
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to trip planner" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#trip-planner$/);
  await page.route("**/api/route", (route) => route.fulfill({ json: plan }));
  await page.getByRole("button", { name: "Plan my route" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".results-focus")).toBeFocused();
  await expect(page.getByText("Browser test pump")).toBeVisible();
  await expect(page.locator(".leaflet-container")).toHaveCount(0);
});
