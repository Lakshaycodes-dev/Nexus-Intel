"""AI voice briefing endpoints (ElevenLabs).

Additive feature: reads the caller's stored analysis records and summarizes the
market changes recorded in the last 24 hours or last 7 days.

* ``GET  /api/v1/briefing/changes?window=24h|7d`` -> JSON summary + script
* ``POST /api/v1/briefing/voice``                  -> MP3 audio of that script

Both endpoints reuse the existing ``get_current_user`` dependency, so a briefing
always belongs to the authenticated workspace. The ElevenLabs key never leaves
the backend.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Response, status
from pymongo.errors import PyMongoError

from app.auth import get_current_user
from app.database import AnalysisRepository, get_repository
from app.errors import ApiException, DatabaseUnavailableError
from app.schemas import BriefingRequest, BriefingSummary, BriefingWindow
from app.services import voice_briefing

logger = logging.getLogger("nexus_intel.api")

router = APIRouter(tags=["briefing"], prefix="/briefing")


async def _build_summary(
    window: BriefingWindow,
    repository: AnalysisRepository,
    user_id: str,
) -> BriefingSummary:
    """Load the workspace's runs in the window and build the digest."""
    reference = datetime.now(timezone.utc)
    since = voice_briefing.since_for(window, now=reference)
    try:
        records = await repository.list_by_user_since(user_id, since)
    except PyMongoError as exc:
        raise DatabaseUnavailableError() from exc
    return voice_briefing.build_briefing(records, window=window, now=reference)


@router.get(
    "/changes",
    response_model=BriefingSummary,
    summary="Summarize competitor changes in a window",
)
async def get_briefing_changes(
    window: BriefingWindow = Query(
        default="24h",
        description="Look-back window: '24h' (last 24 hours) or '7d' (last 7 days).",
    ),
    repository: AnalysisRepository = Depends(get_repository),
    user: dict = Depends(get_current_user),
) -> BriefingSummary:
    """Return the deterministic change digest and the script that will be spoken."""
    return await _build_summary(window, repository, user["user_id"])


@router.post(
    "/voice",
    summary="Generate an ElevenLabs voice briefing (MP3)",
    response_class=Response,
    responses={
        200: {
            "content": {"audio/mpeg": {}},
            "description": "MP3 audio of the selected briefing.",
        },
        502: {"description": "ElevenLabs synthesis failed."},
        503: {"description": "Voice briefing is not configured."},
    },
)
async def create_voice_briefing(
    payload: BriefingRequest,
    repository: AnalysisRepository = Depends(get_repository),
    user: dict = Depends(get_current_user),
) -> Response:
    """Build the digest, synthesize it server-side, and stream back audio."""
    summary = await _build_summary(payload.window, repository, user["user_id"])

    try:
        audio = await voice_briefing.synthesize_speech(summary.script)
    except voice_briefing.VoiceBriefingUnavailable as exc:
        logger.warning("Voice briefing is not configured: %s", exc)
        raise ApiException(
            "voice_briefing_not_configured",
            str(exc),
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc
    except voice_briefing.VoiceBriefingError as exc:
        logger.warning("Voice briefing synthesis failed: %s", exc)
        raise ApiException(
            "voice_briefing_failed",
            str(exc),
            status.HTTP_502_BAD_GATEWAY,
        ) from exc

    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": 'inline; filename="nexus-intel-briefing.mp3"',
            "X-Briefing-Window": payload.window,
            "X-Briefing-Changes": str(len(summary.changes)),
        },
    )
