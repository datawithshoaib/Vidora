"use client";

import { useEffect, useState } from "react";

type HealthStatus = "checking" | "ok" | "unavailable";

export function ServiceStatus() {
  const [status, setStatus] = useState<HealthStatus>("checking");

  useEffect(() => {
    let active = true;
    const check = async () => {
      try {
        const response = await fetch("/api/health", { cache: "no-store" });
        if (active) setStatus(response.ok ? "ok" : "unavailable");
      } catch {
        if (active) setStatus("unavailable");
      }
    };

    void check();
    const timer = window.setInterval(check, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  const connected = status === "ok";
  const label = status === "checking" ? "Checking service" : connected ? "Service online" : "API unavailable";

  return (
    <div aria-live="polite" className="flex items-center gap-2 text-sm text-stone-600">
      <span className={`h-2.5 w-2.5 rounded-full ${connected ? "bg-emerald-500" : status === "unavailable" ? "bg-rose-500" : "animate-pulse bg-amber-400"}`} />
      <span>{label}</span>
      {status === "unavailable" && <span className="text-stone-500">Start the backend with <code>python run.py</code>.</span>}
    </div>
  );
}
