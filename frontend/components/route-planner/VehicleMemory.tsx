"use client";

import { useState } from "react";
import type { VehicleInput } from "@/lib/types";
import { decodeSavedVehicle, vehicleStorageKey } from "@/lib/vehicle-storage";

export function VehicleMemory({ vehicle, onLoad }: { vehicle: VehicleInput; onLoad: (vehicle: VehicleInput) => void }) {
  const [message, setMessage] = useState("");
  function act(action: "save" | "load" | "forget") {
    try {
      if (action === "save") {
        const encoded = JSON.stringify({ version: 1, vehicle });
        if (!decodeSavedVehicle(encoded)) { setMessage("Check your vehicle values before saving."); return; }
        localStorage.setItem(vehicleStorageKey, encoded);
        setMessage("Vehicle saved in this browser.");
      } else if (action === "load") {
        const saved = decodeSavedVehicle(localStorage.getItem(vehicleStorageKey));
        if (!saved) { setMessage("No valid saved vehicle found."); return; }
        onLoad(saved); setMessage("Saved vehicle applied.");
      } else {
        localStorage.removeItem(vehicleStorageKey); setMessage("Saved vehicle removed.");
      }
    } catch { setMessage("Browser storage is unavailable. You can still enter your vehicle details."); }
  }
  return <div className="vehicle-memory">
    <div className="inline-actions">
      <button type="button" onClick={() => act("save")}>Save vehicle</button>
      <button type="button" onClick={() => act("load")}>Use saved vehicle</button>
      <button type="button" onClick={() => act("forget")}>Forget saved vehicle</button>
    </div>
    <p role="status">{message || "Saved in this browser only."}</p>
  </div>;
}
