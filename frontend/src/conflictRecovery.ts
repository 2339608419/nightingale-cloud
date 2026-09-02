import type { EntryVersionConflictDetail } from "./types.ts";

export interface EditConflictState {
  draft: string;
  conflict: EntryVersionConflictDetail | null;
}

export const preserveDraftOnConflict = (
  draft: string,
  conflict: EntryVersionConflictDetail,
): EditConflictState => ({ draft, conflict });

export const cancelConflictAndKeepDraft = (
  state: EditConflictState,
): EditConflictState => ({ ...state, conflict: null });

export const reloadCurrentServerVersion = (
  state: EditConflictState,
): EditConflictState => ({
  draft: state.conflict?.current_content ?? state.draft,
  conflict: null,
});
