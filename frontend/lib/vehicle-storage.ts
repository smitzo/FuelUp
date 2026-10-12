import type { VehicleInput } from "@/lib/types";

export const vehicleStorageKey = "fuelup:vehicle:v1";

export function decodeSavedVehicle(raw: string | null): VehicleInput | null {
  if (!raw || raw.length > 2048) return null;
  try {
    const saved: unknown = JSON.parse(raw);
    if (!saved || typeof saved !== "object" || !("version" in saved) || saved.version !== 1 || !("vehicle" in saved)) return null;
    const vehicle = saved.vehicle as Record<string, unknown> | null;
    if (!vehicle || typeof vehicle !== "object") return null;
    if (vehicle.fuel_type !== "petrol" && vehicle.fuel_type !== "diesel") return null;
    const { tank_capacity: tank, efficiency, starting_fuel: start, reserve_fuel: reserve } = vehicle;
    if (![tank, efficiency, start, reserve].every((value) => typeof value === "number" && Number.isFinite(value))) return null;
    if (typeof tank !== "number" || typeof efficiency !== "number" || typeof start !== "number" || typeof reserve !== "number") return null;
    if (tank < 1 || tank > 300 || efficiency < 1 || efficiency > 100 || start < 0 || reserve < 0 || start + reserve > tank || reserve >= tank) return null;
    return { fuel_type: vehicle.fuel_type, tank_capacity: tank, efficiency, starting_fuel: start, reserve_fuel: reserve };
  } catch { return null; }
}
