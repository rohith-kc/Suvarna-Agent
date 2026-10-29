"""STUB — Phase 0 scaffold only.

Built in Phase 7 (CLAUDE.md Part 5.7): FastAPI POST /elevenlabs/post-call,
verifies the ElevenLabs-Signature HMAC against ELEVENLABS_WEBHOOK_SECRET,
stores conversation_id, transcript, data_collection_results and
evaluation_criteria_results in SQLite, dedupes on conversation_id,
responds 200 immediately.
"""

from fastapi import FastAPI

app = FastAPI()
