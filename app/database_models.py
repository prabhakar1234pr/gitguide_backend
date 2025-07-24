from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

Base = declarative_base()

class TaskStatus(PyEnum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"

class Project(Base):
    __tablename__ = "projects"

    project_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    repo_url = Column(String, nullable=False)
    skill_level = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    
    # New fields for rich learning content
    project_overview = Column(Text, nullable=True)  # AI-generated project overview
    repo_name = Column(String, nullable=True)  # Repository name from GitHub
    tech_stack = Column(Text, nullable=True)  # JSON string of detected technologies
    is_processed = Column(Boolean, default=False, nullable=False)  # Whether agent has processed
    
    # Add unique constraint to prevent duplicate projects for same user and repo
    __table_args__ = (
        UniqueConstraint('user_id', 'repo_url', name='unique_user_repo'),
    )
    
    # Relationships
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    concepts = relationship("Concept", back_populates="project", cascade="all, delete-orphan")

class Concept(Base):
    __tablename__ = "concepts"
    
    concept_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    concept_external_id = Column(String, nullable=False)  # e.g., "concept-0"
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)
    is_unlocked = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="concepts")
    subtopics = relationship("Subtopic", back_populates="concept", cascade="all, delete-orphan")

class Subtopic(Base):
    __tablename__ = "subtopics"
    
    subtopic_id = Column(Integer, primary_key=True, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.concept_id"), nullable=False)
    subtopic_external_id = Column(String, nullable=False)  # e.g., "subtopic-0-0"
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)
    is_unlocked = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    concept = relationship("Concept", back_populates="subtopics")
    tasks = relationship("Task", back_populates="subtopic", cascade="all, delete-orphan")

class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    subtopic_id = Column(Integer, ForeignKey("subtopics.subtopic_id"), nullable=True)  # New relationship
    task_external_id = Column(String, nullable=True)  # e.g., "task-0-0-0"
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)  # Changed to Text for longer descriptions
    status = Column(Enum(TaskStatus), default=TaskStatus.not_started, nullable=False)
    order = Column(Integer, nullable=False)  # For sequential display
    difficulty = Column(String, nullable=True)  # easy, medium, hard
    files_to_study = Column(Text, nullable=True)  # JSON array of file paths
    is_unlocked = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    subtopic = relationship("Subtopic", back_populates="tasks") 