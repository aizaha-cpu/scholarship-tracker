import datetime as dt
from sqlalchemy import create_engine, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

engine = create_engine("sqlite:///./app.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    password: Mapped[str]
    full_name: Mapped[str] = mapped_column(default="")
    degree_level: Mapped[str] = mapped_column(default="")   # bachelors/masters/phd
    field: Mapped[str] = mapped_column(default="")
    gpa: Mapped[float | None] = mapped_column(default=None)  # 4.0 scale
    country: Mapped[str] = mapped_column(default="")
    opportunities = relationship("Opportunity", back_populates="user", cascade="all, delete-orphan")

class Opportunity(Base):
    __tablename__ = "opportunities"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str]
    organization: Mapped[str] = mapped_column(default="")
    deadline: Mapped[dt.date | None] = mapped_column(default=None)
    requirements: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(default="saved")  # saved/applied/won/rejected
    raw_text: Mapped[str] = mapped_column(default="")
    user = relationship("User", back_populates="opportunities")
    items = relationship("DocItem", back_populates="opportunity", cascade="all, delete-orphan")

class DocItem(Base):
    __tablename__ = "doc_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id"))
    name: Mapped[str]
    done: Mapped[bool] = mapped_column(default=False)
    opportunity = relationship("Opportunity", back_populates="items")

class Reminder(Base):  # prevents duplicate reminder emails
    __tablename__ = "reminders"
    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int]
    days_before: Mapped[int]

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
