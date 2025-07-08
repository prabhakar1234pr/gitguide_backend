from sqlalchemy import Column, Integer, String
from app.db import Base

class Project(Base):
    __tablename__ = "projects"

    project_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    repo_url = Column(String, nullable=False)
    skill_level = Column(String, nullable=False)
    domain = Column(String, nullable=False)
