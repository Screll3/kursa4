from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .db import get_db
from .models import EventLog
from .security import get_current_user_id

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get(
    "/events",
    summary="Мои события",
    description="Возвращает последние 50 событий (логов), связанных с действиями текущего пользователя. События формируются асинхронно через RabbitMQ.",
)
def my_events(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """Возвращает последние 50 событий текущего пользователя из таблицы event_logs."""
    rows = (
        db.query(EventLog)
        .filter(EventLog.user_id == user_id)
        .order_by(EventLog.id.desc())
        .limit(50)
        .all()
    )
    return [
        {"id": r.id, "event_type": r.event_type, "payload_json": r.payload_json, "created_at": str(r.created_at)}
        for r in rows
    ]
