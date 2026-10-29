"""STUB — Phase 0 scaffold only.

Built in Phase 4 (CLAUDE.md Part 5.5): a deterministic fake LLM client
returning canned agent/customer/judge responses, used by --dry-run and CI
so the pipeline is exercised fully offline.
"""


class FakeClient:
    def complete(self, role, messages, json_schema=None):
        raise NotImplementedError("Phase 4: implement per CLAUDE.md Part 5.5")
