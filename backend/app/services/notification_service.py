"""Notification Service
Handles transactional and proactive Career OS notifications:
- 7-Day Pro Trial milestones (day 5, day 7)
- Follow-up reminders for submitted applications
- Mock interview practice prompts
- Job Radar match alerts
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.subscription import Subscription
from app.models.application import JobApplication


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notif_type: str = "INFO",
    action_url: str = ""
) -> Notification:
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notif_type,
        action_url=action_url,
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def get_user_notifications(db: Session, user_id: int, unread_only: bool = False) -> list[Notification]:
    query = db.query(Notification).filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc()).limit(50).all()


def mark_as_read(db: Session, user_id: int, notification_id: int) -> bool:
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if not notif:
        return False
    notif.is_read = True
    db.commit()
    return True


def mark_all_as_read(db: Session, user_id: int) -> int:
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read.is_(False)
    ).update({"is_read": True})
    db.commit()
    return count


def check_and_trigger_alerts(db: Session, user_id: int) -> int:
    """Checks for trial expiration and pending application follow-ups."""
    triggered = 0

    # 1. Trial Expiry check
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if sub and sub.is_trial and sub.trial_expires_at:
        now = datetime.utcnow()
        if sub.trial_expires_at > now:
            days_left = (sub.trial_expires_at - now).days
            if days_left <= 2:
                # Check if already notified
                existing = db.query(Notification).filter(
                    Notification.user_id == user_id,
                    Notification.type == "TRIAL"
                ).first()
                if not existing:
                    create_notification(
                        db=db,
                        user_id=user_id,
                        title="Pro Trial Ending Soon",
                        message=f"Your 7-day Pro Trial has {days_left} day(s) remaining. You will never be charged automatically.",
                        notif_type="TRIAL",
                        action_url="#billing"
                    )
                    triggered += 1

    # 2. Application Follow-ups
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    pending_apps = db.query(JobApplication).filter(
        JobApplication.user_id == user_id,
        JobApplication.follow_up_date != "",
        JobApplication.follow_up_date <= today_str,
        JobApplication.status.in_(["APPLIED", "SUBMITTED", "INTERVIEW"])
    ).all()

    for app in pending_apps:
        existing = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.type == "FOLLOW_UP",
            Notification.message.like(f"%{app.company}%")
        ).first()
        if not existing:
            create_notification(
                db=db,
                user_id=user_id,
                title=f"Follow-up Due: {app.company}",
                message=f"It's time to follow up on your {app.job_title} application at {app.company}. Use the template in your Application Pack.",
                notif_type="FOLLOW_UP",
                action_url="#applications"
            )
            triggered += 1

    return triggered
