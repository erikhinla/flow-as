"""
Concierge Booking API.

POST /v1/concierge/book            - create a booking (concierge tier)
GET  /v1/concierge/bookings        - list my bookings
GET  /v1/concierge/bookings/{id}   - get single booking
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_tier
from app.config.database import get_db_session
from app.models.concierge_booking import ConciergeBooking
from app.schemas.concierge import ConciergeBookingRequest, ConciergeBookingResponse

router = APIRouter(prefix="/concierge", tags=["concierge"])

_CONCIERGE_ONLY = ("concierge",)


def _serialize(booking: ConciergeBooking) -> ConciergeBookingResponse:
    return ConciergeBookingResponse(
        booking_id=booking.booking_id,
        user_id=booking.user_id,
        status=booking.status,
        goals=booking.goals,
        context_data=booking.context_data,
        created_at=booking.created_at.isoformat(),
    )


@router.post("/book", response_model=ConciergeBookingResponse, status_code=status.HTTP_201_CREATED)
async def book_concierge(
    payload: ConciergeBookingRequest,
    claims: dict = Depends(require_tier(*_CONCIERGE_ONLY)),
    db: AsyncSession = Depends(get_db_session),
) -> ConciergeBookingResponse:
    """
    Submit a Concierge booking request.

    Requires: **concierge** tier JWT.

    The booking is created in **pending** status. An operator (or future
    automation) will confirm it and reach out to schedule the first session.
    """
    context = {
        "current_situation": payload.current_situation,
        "preferred_timeline": payload.preferred_timeline,
        **payload.extra_context,
    }
    booking = ConciergeBooking(
        user_id=claims["sub"],
        goals=payload.goals,
        context_data=context,
    )
    db.add(booking)
    await db.commit()
    await db.refresh(booking)
    return _serialize(booking)


@router.get("/bookings", response_model=list[ConciergeBookingResponse])
async def list_bookings(
    claims: dict = Depends(require_tier(*_CONCIERGE_ONLY)),
    db: AsyncSession = Depends(get_db_session),
) -> list[ConciergeBookingResponse]:
    """
    List all concierge bookings for the authenticated user.

    Requires: **concierge** tier JWT.
    """
    result = await db.execute(
        select(ConciergeBooking)
        .where(ConciergeBooking.user_id == claims["sub"])
        .order_by(ConciergeBooking.created_at.desc())
    )
    return [_serialize(b) for b in result.scalars().all()]


@router.get("/bookings/{booking_id}", response_model=ConciergeBookingResponse)
async def get_booking(
    booking_id: str,
    claims: dict = Depends(require_tier(*_CONCIERGE_ONLY)),
    db: AsyncSession = Depends(get_db_session),
) -> ConciergeBookingResponse:
    """
    Retrieve a single concierge booking by ID.

    Requires: **concierge** tier JWT.  Users can only access their own bookings.
    """
    result = await db.execute(
        select(ConciergeBooking).where(ConciergeBooking.booking_id == booking_id)
    )
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found.")
    if booking.user_id != claims["sub"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    return _serialize(booking)
