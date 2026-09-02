import assert from "node:assert/strict";
import test from "node:test";

import { ApiError } from "../src/api.ts";
import {
  cancelConflictAndKeepDraft,
  preserveDraftOnConflict,
  reloadCurrentServerVersion,
} from "../src/conflictRecovery.ts";

const detail = {
  error_code: "entry_version_conflict" as const,
  entry_id: "entry-demo-001",
  expected_version: 1,
  current_version: 2,
  current_content: "Server v2",
  current_provenance_pointer: null,
};

test("ApiError retains structured conflict detail", () => {
  const error = new ApiError(409, detail);
  assert.equal(error.status, 409);
  assert.deepEqual(error.detail, detail);
});

test("cancel keeps the unsaved local draft", () => {
  const state = preserveDraftOnConflict("My local clinical draft", detail);
  assert.equal(state.draft, "My local clinical draft");
  assert.equal(cancelConflictAndKeepDraft(state).draft, "My local clinical draft");
});

test("reload is explicit and replaces draft with current server content", () => {
  const state = preserveDraftOnConflict("My local clinical draft", detail);
  assert.deepEqual(reloadCurrentServerVersion(state), {
    draft: "Server v2",
    conflict: null,
  });
});
