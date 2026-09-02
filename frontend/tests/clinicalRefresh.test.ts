import assert from "node:assert/strict";
import test from "node:test";
import { createClinicalRefresh, clinicalSyncMessage } from "../src/clinicalRefresh.ts";
import { createScribeController, parseScribeResponse } from "../src/aiScribeRecovery.ts";

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

test("created entry refreshes Glance/conflicts/evidence without resetting success or draft", async () => {
  const pending = deferred<{ highlights: string[]; conflicts: string[]; evidence: string }>();
  let snapshot = { highlights: ["old"], conflicts: [] as string[], evidence: "HIGH" };
  const statuses: string[] = [];
  let refreshPromise: Promise<void> | undefined;
  const refresh = createClinicalRefresh(() => pending.promise, (value) => { snapshot = value; }, (value) => statuses.push(value));
  let generationCalls = 0;
  const scribe = createScribeController("patient-demo-001", { userId: "clinician", role: "clinician", clinicId: "clinic" }, async () => {
    generationCalls++;
    return parseScribeResponse(201, { status: "created", outcome: "success", safe_abstention: false,
      generation_mode: "rule_derived_mock", generated_summary: "Synthetic allergy statement",
      provenance_pointer: "synthetic://source", timeline_entry: { id: "new", patient_id: "patient-demo-001",
        author_role: "system", type: "ai_doctor_consult_summary", content: "Synthetic allergy statement" } }, "patient-demo-001");
  }, () => { refreshPromise = refresh.refresh(); });
  scribe.edit("Synthetic draft"); await scribe.submit();
  assert.equal(scribe.getSnapshot().phase, "success");
  assert.equal(scribe.getSnapshot().draft, "Synthetic draft");
  assert.deepEqual(statuses, ["refreshing"]);
  pending.resolve({ highlights: ["allergy warning"], conflicts: ["allergy conflict"], evidence: "ABSTAIN" });
  await refreshPromise;
  assert.deepEqual(snapshot, { highlights: ["allergy warning"], conflicts: ["allergy conflict"], evidence: "ABSTAIN" });
  assert.deepEqual(statuses, ["refreshing", "current"]);
  assert.equal(scribe.canSubmit(), false); await scribe.submit(); assert.equal(generationCalls, 1);
  // A later read failure is independent of the already-committed generation.
  const failedRead = createClinicalRefresh(async () => { throw new Error("read failed"); }, () => assert.fail(), (value) => statuses.push(value));
  await failedRead.refresh();
  assert.equal(statuses.at(-1), "stale");
  assert.equal(scribe.getSnapshot().phase, "success");
  assert.equal(scribe.getSnapshot().draft, "Synthetic draft");
  await scribe.submit(); assert.equal(generationCalls, 1);
});

test("refresh failure marks safety views stale; read-only retry does not regenerate", async () => {
  const statuses: string[] = []; let applied = 0; let reads = 0;
  const refresh = createClinicalRefresh(async () => { reads++; if (reads === 1) throw new Error("private error"); return "new evidence"; },
    () => { applied++; }, (value) => statuses.push(value));
  await refresh.refresh();
  assert.deepEqual(statuses, ["refreshing", "stale"]); assert.equal(applied, 0);
  assert.match(clinicalSyncMessage.stale, /Generation succeeded/);
  assert.match(clinicalSyncMessage.stale, /NOT UPDATED/);
  assert.match(clinicalSyncMessage.stale, /Do not regenerate/);
  await refresh.refresh(); assert.equal(reads, 2); assert.equal(applied, 1);
  assert.deepEqual(statuses, ["refreshing", "stale", "refreshing", "current"]);
});

test("identity/patient switch ignores both late refresh success and late failure", async () => {
  for (const fail of [false, true]) {
    const pending = deferred<string>(); const applied: string[] = []; const statuses: string[] = [];
    const old = createClinicalRefresh(() => pending.promise, (value) => applied.push(value), (value) => statuses.push(value));
    const running = old.refresh(); old.dispose();
    if (fail) pending.reject(new Error("old context error")); else pending.resolve("old patient evidence");
    await running;
    assert.deepEqual(applied, []); assert.deepEqual(statuses, ["refreshing"]);
  }
});

test("only latest safety refresh can publish a snapshot", async () => {
  const first = deferred<string>(); const second = deferred<string>(); let reads = 0;
  const applied: string[] = [];
  const refresh = createClinicalRefresh(() => ++reads === 1 ? first.promise : second.promise, (value) => applied.push(value), () => {});
  const old = refresh.refresh(); const recent = refresh.refresh();
  second.resolve("latest"); await recent; first.resolve("obsolete"); await old;
  assert.deepEqual(applied, ["latest"]);
});
