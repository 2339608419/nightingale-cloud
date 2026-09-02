import assert from "node:assert/strict";
import test from "node:test";
import { createScribeController, parseScribeResponse, scribeMessages } from "../src/aiScribeRecovery.ts";
import type { ScribeOutcome, ScribeResult } from "../src/aiScribeRecovery.ts";
import { submitAiScribe } from "../src/api.ts";
import type { ApiIdentity } from "../src/types.ts";

const identity: ApiIdentity = { userId: "clinician-demo-001", role: "clinician", clinicId: "clinic-demo-001" };
const patient = "patient-demo-001";
const draft = "Synthetic Lisinopril 10 mg daily.";
const entry = { id: "ai-entry", patient_id: patient, content: draft, author_role: "system", type: "ai_doctor_consult_summary" };
function body(outcome: ScribeOutcome = "success", mode = "rule_derived_mock") {
  return { outcome, status: outcome === "success" ? "created" : "withheld", generation_mode: mode,
    safe_abstention: outcome !== "success", generated_summary: outcome === "success" ? draft : null,
    timeline_entry: outcome === "success" ? entry : null,
    provenance_pointer: outcome === "success" ? "synthetic://opaque#transcript" : null };
}
function deferred() {
  let resolve!: (value: ScribeResult) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<ScribeResult>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

test("waiting locks duplicate submission synchronously; success delivers exactly once", async () => {
  const pending = deferred(); let calls = 0; const created: unknown[] = [];
  const control = createScribeController(patient, identity, async (payload) => {
    calls++; assert.equal(payload.transcript, draft); assert.equal(payload.synthetic, true);
    assert.match(payload.source_id, /^scribe-/); return pending.promise;
  }, (value) => created.push(value));
  control.edit(draft);
  const first = control.submit();
  assert.equal(control.getSnapshot().phase, "waiting"); assert.equal(control.canSubmit(), false);
  control.edit("must not replace in-flight draft");
  await control.submit(); assert.equal(calls, 1);
  pending.resolve(parseScribeResponse(201, body(), patient)); await first;
  assert.equal(control.getSnapshot().phase, "success");
  assert.equal(control.getSnapshot().draft, draft); assert.equal(created.length, 1);
  await control.submit(); assert.equal(calls, 1);
  control.newDraft(); assert.equal(control.getSnapshot().draft, "");
});

for (const [outcome, status] of [
  ["redaction_withheld", 200], ["provider_timeout", 504],
  ["provider_unavailable", 503], ["invalid_provider_response", 502],
] as const) {
  test(`${outcome}: retains draft, no fake summary/content mutation; explicit retry only`, async () => {
    let calls = 0; const clinicalContent = ["Existing clinician plan"];
    const control = createScribeController(patient, identity, async () => {
      calls++; return parseScribeResponse(status, body(outcome), patient);
    }, (value) => clinicalContent.push(value.content));
    control.edit(draft); await control.submit();
    assert.equal(calls, 1); assert.equal(control.getSnapshot().phase, outcome);
    assert.equal(control.getSnapshot().draft, draft); assert.equal(control.getSnapshot().summary, null);
    assert.deepEqual(clinicalContent, ["Existing clinician plan"]);
    assert.equal(control.canSubmit(), true);
    await Promise.resolve(); assert.equal(calls, 1);
    control.edit("Corrected synthetic draft"); await control.submit();
    assert.equal(calls, 2); assert.equal(control.getSnapshot().draft, "Corrected synthetic draft");
  });
}

test("network loss is unknown and cannot be retried, even after editing", async () => {
  let calls = 0;
  const control = createScribeController(patient, identity, async () => { calls++; throw new Error("sensitive network error"); }, () => assert.fail());
  control.edit(draft); await control.submit();
  assert.equal(control.getSnapshot().phase, "unknown");
  assert.equal(control.getSnapshot().draft, draft); assert.equal(control.canSubmit(), false);
  assert.match(scribeMessages.unknown, /refresh and check Timeline/);
  control.edit("Changed draft"); control.newDraft(); await control.submit(); assert.equal(calls, 1);
  assert.equal(JSON.stringify(control.getSnapshot()).includes("sensitive network error"), false);
});

test("patient or identity switch clears memory and ignores late success and failure", async () => {
  for (const failed of [false, true]) {
    const pending = deferred(); const changed: unknown[] = [];
    const old = createScribeController(patient, identity, () => pending.promise, (value) => changed.push(value));
    old.edit(draft); const running = old.submit(); old.dispose();
    const next = createScribeController("patient-other", { ...identity, userId: "other" }, async () => { throw new Error(); }, () => assert.fail());
    assert.equal(old.getSnapshot().draft, ""); assert.equal(next.getSnapshot().draft, "");
    if (failed) pending.reject(new Error("late error")); else pending.resolve(parseScribeResponse(201, body(), patient));
    await running;
    assert.equal(next.getSnapshot().phase, "idle"); assert.equal(old.getSnapshot().phase, "idle");
    assert.deepEqual(changed, []);
  }
});

test("generation mode comes from validated response, not assumed mock success", () => {
  for (const mode of ["external_model", "rule_derived_mock", "test_double"] as const) {
    assert.equal(parseScribeResponse(201, body("success", mode), patient).generation_mode, mode);
  }
  assert.throws(() => parseScribeResponse(201, body("success", "invented"), patient));
  assert.throws(() => parseScribeResponse(201, body(), "wrong-patient"));
});

test("HTTP adapter preserves root abstention bodies on 502/503/504 and sends one POST", async () => {
  const originalFetch = globalThis.fetch;
  try {
    for (const [outcome, status] of [["provider_timeout", 504], ["provider_unavailable", 503], ["invalid_provider_response", 502]] as const) {
      let calls = 0;
      globalThis.fetch = async (_input, init) => {
        calls++; assert.equal(init?.method, "POST"); assert.equal(init?.cache, "no-store");
        return new Response(JSON.stringify(body(outcome)), { status });
      };
      const result = await submitAiScribe({ patient_id: patient, interaction_type: "doctor_consult", source_id: "synthetic-source", transcript: draft, synthetic: true }, identity);
      assert.equal(result.outcome, outcome); assert.equal(calls, 1);
    }
  } finally { globalThis.fetch = originalFetch; }
});

test("proxy errors, lost/malformed success and inconsistent abstention remain unknown", async () => {
  for (const [status, response] of [[503, { detail: "upstream error" }], [201, {}],
    [201, { ...body(), generated_summary: "" }], [504, { ...body("provider_timeout"), timeline_entry: entry }]] as const) {
    const control = createScribeController(patient, identity, async () => parseScribeResponse(status, response, patient), () => assert.fail());
    control.edit(draft); await control.submit();
    assert.equal(control.getSnapshot().phase, "unknown"); assert.equal(control.canSubmit(), false);
    assert.equal(control.getSnapshot().summary, null);
  }
});

test("authorization/validation errors use fixed safe messages and keep draft", async () => {
  for (const status of [401, 403, 404, 422]) {
    const control = createScribeController(patient, identity, async () => parseScribeResponse(status, { detail: draft }, patient), () => assert.fail());
    control.edit(draft); await control.submit();
    assert.equal(control.getSnapshot().phase, "request_rejected");
    assert.equal(control.getSnapshot().draft, draft); assert.equal(control.getSnapshot().summary, null);
  }
});
