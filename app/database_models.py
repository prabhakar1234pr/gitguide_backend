from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, Enum, UniqueConstraint, Float
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
    
    # Progress tracking
    total_days = Column(Integer, default=14, nullable=False)  # Total days in curriculum
    completed_days = Column(Integer, default=0, nullable=False)  # Days completed
    current_day = Column(Integer, default=0, nullable=False)  # Current day user is on
    project_progress = Column(Float, default=0.0, nullable=False)  # Overall project progress (0.0-1.0)
    
    # Add unique constraint to prevent duplicate projects for same user and repo
    __table_args__ = (
        UniqueConstraint('user_id', 'repo_url', name='unique_user_repo'),
    )
    
    # Relationships
    days = relationship("Day", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project", cascade="all, delete-orphan")  # Keep for backward compatibility
    concepts = relationship("Concept", back_populates="project", cascade="all, delete-orphan")  # Keep for backward compatibility

class Day(Base):
    __tablename__ = "days"
    
    day_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)
    day_number = Column(Integer, nullable=False)  # 0-14 (Day 0 for verification)
    day_external_id = Column(String, nullable=False)  # e.g., "day-0", "day-1", "day-2"
    name = Column(String, nullable=False)  # e.g., "Day 0: Setup Repository"
    description = Column(Text, nullable=True)  # What will be learned on this day
    is_unlocked = Column(Boolean, default=False, nullable=False)  # Only day 0 should be unlocked initially
    is_completed = Column(Boolean, default=False, nullable=False)  # Track completion
    order = Column(Integer, nullable=False)  # Same as day_number for ordering
    
    # Progress tracking
    total_tasks = Column(Integer, default=100, nullable=False)  # 10 concepts × 10 subconcepts × 1 task
    completed_tasks = Column(Integer, default=0, nullable=False)  # Tasks completed
    day_progress = Column(Float, default=0.0, nullable=False)  # Day progress (0.0-1.0)
    
    # Content generation status
    is_content_generated = Column(Boolean, default=False, nullable=False)  # Whether content is ready
    content_generation_started = Column(Boolean, default=False, nullable=False)  # Whether generation is in progress
    
    # Verification fields for Day 0
    requires_verification = Column(Boolean, default=False, nullable=False)  # True for Day 0
    verification_repo_url = Column(String, nullable=True)  # User's GitHub repo URL
    is_verified = Column(Boolean, default=False, nullable=False)  # GitHub repo verification status
    
    # Add unique constraint to prevent duplicate days for same project
    __table_args__ = (
        UniqueConstraint('project_id', 'day_number', name='unique_project_day'),
    )
    
    # Relationships
    project = relationship("Project", back_populates="days")
    concepts = relationship("Concept", back_populates="day", cascade="all, delete-orphan")

class Concept(Base):
    __tablename__ = "concepts"
    
    concept_id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.project_id"), nullable=False)  # Keep for backward compatibility
    day_id = Column(Integer, ForeignKey("days.day_id"), nullable=True)  # New relationship to Day
    concept_external_id = Column(String, nullable=False)  # e.g., "concept-0"
    title = Column(String, nullable=False)  # Changed from 'name' to 'title' to match frontend
    description = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)
    is_unlocked = Column(Boolean, default=False, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)  # Track completion for Day 0 concepts
    
    # Progress tracking
    total_subconcepts = Column(Integer, default=10, nullable=False)  # 10 subconcepts per concept
    completed_subconcepts = Column(Integer, default=0, nullable=False)  # Subconcepts completed
    concept_progress = Column(Float, default=0.0, nullable=False)  # Concept progress (0.0-1.0)
    
    # Relationships
    project = relationship("Project", back_populates="concepts")  # Keep for backward compatibility
    day = relationship("Day", back_populates="concepts")  # New relationship
    subtopics = relationship("Subtopic", back_populates="concept", cascade="all, delete-orphan")  # Keep for backward compatibility
    subconcepts = relationship("Subconcept", back_populates="concept", cascade="all, delete-orphan")  # New: Subconcepts
    tasks = relationship("Task", back_populates="concept", cascade="all, delete-orphan")  # New: Direct concept tasks

# New Subconcept model for the updated structure
class Subconcept(Base):
    __tablename__ = "subconcepts"
    
    subconcept_id = Column(Integer, primary_key=True, index=True)
    concept_id = Column(Integer, ForeignKey("concepts.concept_id"), nullable=False)
    subconcept_external_id = Column(String, nullable=False)  # e.g., "subconcept-0-0"
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)
    is_unlocked = Column(Boolean, default=False, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)  # Track completion
    
    # Relationships
    concept = relationship("Concept", back_populates="subconcepts")
    task = relationship("Task", back_populates="subconcept", uselist=False, cascade="all, delete-orphan")  # One task per subconcept

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
    concept_id = Column(Integer, ForeignKey("concepts.concept_id"), nullable=True)  # New: Direct concept tasks (Day 0)
    subtopic_id = Column(Integer, ForeignKey("subtopics.subtopic_id"), nullable=True)  # Existing: Subtopic tasks (backward compatibility)
    subconcept_id = Column(Integer, ForeignKey("subconcepts.subconcept_id"), nullable=True)  # New: Subconcept tasks
    task_external_id = Column(String, nullable=True)  # e.g., "task-0-0-0"
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)  # Changed to Text for longer descriptions
    status = Column(Enum(TaskStatus), default=TaskStatus.not_started, nullable=False)
    order = Column(Integer, nullable=False)  # For sequential display
    difficulty = Column(String, nullable=True)  # easy, medium, hard
    files_to_study = Column(Text, nullable=True)  # JSON array of file paths
    is_unlocked = Column(Boolean, default=False, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)  # Track completion for Day 0 tasks
    
    # GitHub verification fields
    verification_type = Column(String, nullable=True)  # 'github_profile', 'repository_creation', 'commit_verification', 'github_api'
    verification_data = Column(Text, nullable=True)  # JSON data for verification (URLs, etc.)
    is_verified = Column(Boolean, default=False, nullable=False)  # Verification status
    github_verification_status = Column(String, nullable=True)  # 'pending', 'verified', 'failed'
    github_check_url = Column(String, nullable=True)  # URL or identifier for GitHub verification
    
    # Relationships
    project = relationship("Project", back_populates="tasks")
    concept = relationship("Concept", back_populates="tasks")  # New: Direct concept relationship
    subtopic = relationship("Subtopic", back_populates="tasks")  # Existing: Subtopic relationship (backward compatibility)
    subconcept = relationship("Subconcept", back_populates="task")  # New: Subconcept relationship 