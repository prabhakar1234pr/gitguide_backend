import asyncio
from app.database_config import SessionLocal
from app.database_models import Project, Concept, Subtopic, Task
from sqlalchemy import select

async def check_database():
    """Check what's actually saved in the database"""
    async with SessionLocal() as session:
        # Check concepts
        concepts = await session.execute(select(Concept))
        concept_list = concepts.scalars().all()
        print(f"📊 Concepts: {len(concept_list)}")
        for c in concept_list:
            print(f"  - {c.name} (ID: {c.concept_id}, Project: {c.project_id})")
        
        # Check subtopics
        subtopics = await session.execute(select(Subtopic))
        subtopic_list = subtopics.scalars().all()
        print(f"\n📊 Subtopics: {len(subtopic_list)}")
        for s in subtopic_list:
            print(f"  - {s.name} (ID: {s.subtopic_id}, Concept: {s.concept_id})")
        
        # Check tasks
        tasks = await session.execute(select(Task))
        task_list = tasks.scalars().all()
        print(f"\n📊 Tasks: {len(task_list)}")
        for t in task_list:
            print(f"  - {t.title} (ID: {t.task_id}, Subtopic: {t.subtopic_id})")
        
        # Check projects
        projects = await session.execute(select(Project))
        project_list = projects.scalars().all()
        print(f"\n📊 Projects: {len(project_list)}")
        for p in project_list:
            print(f"  - {p.repo_url} (ID: {p.project_id}, Processed: {p.is_processed})")

if __name__ == "__main__":
    asyncio.run(check_database()) 