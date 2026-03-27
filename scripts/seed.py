from sqlmodel import Session, select

from poseai_backend.auth import get_password_hash
from poseai_backend.database import engine
from poseai_backend.models import Plan, User


def seed() -> None:
    with Session(engine) as session:
        admin = session.exec(select(User).where(User.email == "admin@example.com")).first()
        if not admin:
            admin = User(
                email="admin@example.com",
                hashed_password=get_password_hash("adminpass123"),
                full_name="Admin Coach",
                role="admin",
            )
            session.add(admin)
            session.commit()
            session.refresh(admin)

        existing = session.exec(select(Plan)).first()
        if existing:
            return

        plans = [
            Plan(
                owner_id=admin.id,
                title="Beginner squat setup",
                goal="Build a stable bodyweight squat pattern",
                cues="Brace the core, keep the chest tall, push the floor away, and keep knees tracking over the toes.",
                level="Beginner",
                is_public=True,
            ),
            Plan(
                owner_id=admin.id,
                title="Tempo squat control",
                goal="Improve control on the way down",
                cues="Descend for 3 seconds, pause briefly at the bottom, and stand up with steady speed.",
                level="Intermediate",
                is_public=True,
            ),
        ]
        session.add_all(plans)
        session.commit()


if __name__ == "__main__":
    seed()
