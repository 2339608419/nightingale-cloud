export type ClinicalSync = "current" | "refreshing" | "stale";
export const clinicalSyncMessage = {
  current: "Clinical safety views updated.",
  refreshing: "Generation succeeded. Updating Glance, conflicts and Evidence Confidence; previous safety views are not shown as current.",
  stale: "Generation succeeded, but clinical safety views could not refresh. Glance, conflicts and Evidence Confidence are NOT UPDATED. Do not regenerate; refresh clinical views only.",
};

// All-or-nothing read refresh; never retries generation. Each instance belongs to one context.
export function createClinicalRefresh<T>(
  load: () => Promise<T>, apply: (snapshot: T) => void, status: (value: ClinicalSync) => void,
) {
  let active = true;
  let epoch = 0;
  return {
    activate() { active = true; },
    dispose() { active = false; epoch++; },
    async refresh() {
      if (!active) return;
      const request = ++epoch;
      status("refreshing");
      try {
        const snapshot = await load();
        if (!active || request !== epoch) return;
        apply(snapshot);
        status("current");
      } catch {
        if (active && request === epoch) status("stale");
      }
    },
  };
}
