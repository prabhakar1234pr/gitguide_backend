"""
Days utilities for GitGuide
Helper functions for creating and managing 14-day learning progression
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict, Any

async def create_15_days_for_project(session: AsyncSession, project_id: int, project_name: str = None) -> List[Dict[str, Any]]:
    """
    Create Day 0 (verification) + 14 learning days for a new project
    
    Args:
        session: Database session
        project_id: ID of the project to create days for
        project_name: Name of the project for Day 0 verification requirements
    
    Returns:
        List of created day dictionaries
    """
    days_data = []
    
    # Create Day 0 (verification day)
    day0_name = "Day 0: Setup Your Practice Repository"
    day0_description = f'Create your own GitHub repository named "{project_name or "project"}-gitguide" to practice and track your learning progress. This helps you apply what you learn!'
    
    day0_data = {
        'project_id': project_id,
        'day_number': 0,
        'day_external_id': 'day-0',
        'name': day0_name,
        'description': day0_description,
        'is_unlocked': True,  # Day 0 is always unlocked
        'is_completed': False,
        'order': 0,
        'requires_verification': True,
        'verification_repo_url': None,
        'is_verified': False
    }
    
    # Insert Day 0 into database
    await session.execute(text("""
        INSERT INTO days (project_id, day_number, day_external_id, name, description, 
                         is_unlocked, is_completed, "order", requires_verification, 
                         verification_repo_url, is_verified)
        VALUES (:project_id, :day_number, :day_external_id, :name, :description, 
                :is_unlocked, :is_completed, :order, :requires_verification, 
                :verification_repo_url, :is_verified)
    """), day0_data)
    
    days_data.append(day0_data)
    
    # Define day categories and names for Days 1-14
    day_categories = {
        1: ("Getting Started", "Introduction and setup"),
        2: ("Foundation", "Basic concepts and fundamentals"),
        3: ("Foundation", "Core building blocks"),
        4: ("Core Concepts", "Essential learning components"),
        5: ("Core Concepts", "Key programming patterns"),
        6: ("Core Concepts", "Important implementation details"),
        7: ("Core Concepts", "Advanced fundamentals"),
        8: ("Advanced Topics", "Complex concepts and patterns"),
        9: ("Advanced Topics", "Sophisticated implementations"),
        10: ("Advanced Topics", "Expert-level topics"),
        11: ("Mastery", "Professional practices"),
        12: ("Mastery", "Advanced optimization"),
        13: ("Mastery", "Expert techniques"),
        14: ("Mastery", "Project completion and mastery")
    }
    
    # Create Days 1-14 (all locked until Day 0 verification)
    for day_num in range(1, 15):
        category, description = day_categories[day_num]
        day_name = f"Day {day_num}: {category}"
        
        # All days are locked until Day 0 verification
        is_unlocked = False
        
        day_data = {
            'project_id': project_id,
            'day_number': day_num,
            'day_external_id': f"day-{day_num}",
            'name': day_name,
            'description': f"{description} - Learning objectives for {day_name.lower()}",
            'is_unlocked': is_unlocked,
            'is_completed': False,
            'order': day_num,
            'requires_verification': False,
            'verification_repo_url': None,
            'is_verified': False
        }
        
        # Insert day into database
        await session.execute(text("""
            INSERT INTO days (project_id, day_number, day_external_id, name, description, 
                             is_unlocked, is_completed, "order", requires_verification, 
                             verification_repo_url, is_verified)
            VALUES (:project_id, :day_number, :day_external_id, :name, :description, 
                    :is_unlocked, :is_completed, :order, :requires_verification, 
                    :verification_repo_url, :is_verified)
        """), day_data)
        
        days_data.append(day_data)
    
    await session.commit()
    print(f"✅ Created Day 0 + 14 learning days for project {project_id} (only Day 0 unlocked)")
    
    # 🆕 CREATE DAY 0 CONCEPTS AND TASKS
    try:
        print(f"📝 Creating Day 0 concepts and tasks for project {project_id}")
        await create_day0_concepts_and_tasks(session, project_id)
        print(f"✅ Day 0 concepts and tasks created for project {project_id}")
    except Exception as e:
        print(f"⚠️ Failed to create Day 0 concepts and tasks: {str(e)}")
        # Continue even if concepts creation fails
    
    return days_data

# Keep the old function for backward compatibility, but redirect to new function
async def create_14_days_for_project(session: AsyncSession, project_id: int) -> List[Dict[str, Any]]:
    """
    Legacy function - now creates Day 0 + 14 days
    """
    return await create_15_days_for_project(session, project_id)

async def unlock_next_day(session: AsyncSession, project_id: int, current_day: int) -> bool:
    """
    Unlock the next day ONLY when ALL tasks in current day are completed and verified
    
    Args:
        session: Database session
        project_id: ID of the project
        current_day: Current day number (0-14)
    
    Returns:
        True if next day was unlocked, False if no next day or requirements not met
    """
    next_day = current_day + 1
    
    if next_day > 14:
        print(f"🎉 All days completed for project {project_id}!")
        return False
    
    # STRICT VERIFICATION: Check that ALL tasks in current day are verified
    print(f"🔍 Checking if all tasks in Day {current_day} are verified for project {project_id}")
    
    if current_day == 0:
        # For Day 0: Check that all verification tasks are completed and verified
        result = await session.execute(text("""
            SELECT COUNT(*) as total_tasks, 
                   COUNT(CASE WHEN t.is_verified = TRUE THEN 1 END) as verified_tasks
            FROM tasks t
            JOIN concepts c ON t.concept_id = c.concept_id
            JOIN days d ON c.day_id = d.day_id
            WHERE d.project_id = :project_id AND d.day_number = :current_day
            AND t.verification_type IS NOT NULL
        """), {'project_id': project_id, 'current_day': current_day})
        
        task_counts = result.fetchone()
        total_tasks = task_counts[0] if task_counts else 0
        verified_tasks = task_counts[1] if task_counts else 0
        
        if total_tasks == 0:
            print(f"❌ No verification tasks found for Day {current_day}")
            return False
            
        if verified_tasks < total_tasks:
            print(f"❌ Day {current_day}: Only {verified_tasks}/{total_tasks} tasks verified. Cannot unlock Day {next_day}")
            return False
            
        print(f"✅ Day {current_day}: All {verified_tasks}/{total_tasks} verification tasks completed!")
        
    else:
        # For Days 1-14: Check that all tasks are completed (using existing task completion logic)
        result = await session.execute(text("""
            SELECT COUNT(*) as total_tasks, 
                   COUNT(CASE WHEN t.is_completed = TRUE THEN 1 END) as completed_tasks
            FROM tasks t
            WHERE t.project_id = :project_id
            AND (
                EXISTS (
                    SELECT 1 FROM concepts c 
                    JOIN days d ON c.day_id = d.day_id 
                    WHERE d.day_number = :current_day AND c.concept_id = t.concept_id
                )
                OR EXISTS (
                    SELECT 1 FROM subconcepts sc
                    JOIN concepts c ON sc.concept_id = c.concept_id
                    JOIN days d ON c.day_id = d.day_id
                    WHERE d.day_number = :current_day AND sc.subconcept_id = t.subconcept_id
                )
            )
        """), {'project_id': project_id, 'current_day': current_day})
        
        task_counts = result.fetchone()
        total_tasks = task_counts[0] if task_counts else 0
        completed_tasks = task_counts[1] if task_counts else 0
        
        if total_tasks == 0:
            print(f"❌ No tasks found for Day {current_day}")
            return False
            
        if completed_tasks < total_tasks:
            print(f"❌ Day {current_day}: Only {completed_tasks}/{total_tasks} tasks completed. Cannot unlock Day {next_day}")
            return False
            
        print(f"✅ Day {current_day}: All {completed_tasks}/{total_tasks} tasks completed!")
    
    # Check if next day exists and whether it's unlocked
    result = await session.execute(text("""
        SELECT is_unlocked FROM days 
        WHERE project_id = :project_id AND day_number = :day_number
    """), {'project_id': project_id, 'day_number': next_day})
    current_status = result.scalar_one_or_none()
    if current_status is None:
        print(f"❌ Day {next_day} not found for project {project_id}")
        return False

    # Ensure day row is unlocked
    if not current_status:
        await session.execute(text(
            """
            UPDATE days 
            SET is_unlocked = TRUE 
            WHERE project_id = :project_id AND day_number = :day_number
            """
        ), {'project_id': project_id, 'day_number': next_day})

    # Idempotently unlock concepts and subtopics for the day, and only first task per subtopic
    try:
        # Unlock all concepts for the day
        await session.execute(text(
            """
            UPDATE concepts c
            SET is_unlocked = TRUE
            FROM days d
            WHERE c.day_id = d.day_id AND d.project_id = :project_id AND d.day_number = :day_number
            """
        ), {'project_id': project_id, 'day_number': next_day})

        # Unlock all subtopics for those concepts
        await session.execute(text(
            """
            UPDATE subtopics s
            SET is_unlocked = TRUE
            WHERE s.concept_id IN (
                SELECT c.concept_id FROM concepts c
                JOIN days d ON d.day_id = c.day_id
                WHERE d.project_id = :project_id AND d.day_number = :day_number
            )
            """
        ), {'project_id': project_id, 'day_number': next_day})

        # Unlock only the first task per subtopic; others remain locked
        await session.execute(text(
            """
            WITH subtopic_first_tasks AS (
                SELECT DISTINCT ON (t.subtopic_id) t.task_id
                FROM tasks t
                JOIN subtopics s ON s.subtopic_id = t.subtopic_id
                JOIN concepts c ON c.concept_id = s.concept_id
                JOIN days d ON d.day_id = c.day_id
                WHERE d.project_id = :project_id AND d.day_number = :day_number
                ORDER BY t.subtopic_id, t."order"
            )
            UPDATE tasks AS all_tasks
            SET is_unlocked = CASE
                WHEN all_tasks.task_id IN (SELECT task_id FROM subtopic_first_tasks) THEN TRUE
                ELSE FALSE
            END
            WHERE all_tasks.subtopic_id IN (
                SELECT s.subtopic_id FROM subtopics s
                JOIN concepts c ON c.concept_id = s.concept_id
                JOIN days d ON d.day_id = c.day_id
                WHERE d.project_id = :project_id AND d.day_number = :day_number
            );
            """
        ), {'project_id': project_id, 'day_number': next_day})
    except Exception as _:
        pass

    await session.commit()
    print(f"🔓 Ensured Day {next_day} content unlocked for project {project_id}")
    return True

async def mark_day_completed(session: AsyncSession, project_id: int, day_number: int) -> bool:
    """
    Mark a day as completed ONLY if all tasks are verified/completed
    
    Args:
        session: Database session
        project_id: ID of the project
        day_number: Day number to mark as completed (0-14)
    
    Returns:
        True if day was marked completed successfully, False if requirements not met
    """
    
    # STRICT VERIFICATION: Check that all tasks in the day are verified/completed
    print(f"🔍 Checking if all tasks in Day {day_number} are verified before marking as completed")
    
    if day_number == 0:
        # For Day 0: Check that all verification tasks are completed and verified
        result = await session.execute(text("""
            SELECT COUNT(*) as total_tasks, 
                   COUNT(CASE WHEN t.is_verified = TRUE THEN 1 END) as verified_tasks
            FROM tasks t
            JOIN concepts c ON t.concept_id = c.concept_id
            JOIN days d ON c.day_id = d.day_id
            WHERE d.project_id = :project_id AND d.day_number = :day_number
            AND t.verification_type IS NOT NULL
        """), {'project_id': project_id, 'day_number': day_number})
        
        task_counts = result.fetchone()
        total_tasks = task_counts[0] if task_counts else 0
        verified_tasks = task_counts[1] if task_counts else 0
        
        if total_tasks == 0:
            print(f"❌ No verification tasks found for Day {day_number}")
            return False
            
        if verified_tasks < total_tasks:
            print(f"❌ Cannot mark Day {day_number} as completed: Only {verified_tasks}/{total_tasks} tasks verified")
            return False
            
        print(f"✅ Day {day_number}: All {verified_tasks}/{total_tasks} verification tasks completed!")
        
    else:
        # For Days 1-14: Check that all tasks are completed
        result = await session.execute(text("""
            SELECT COUNT(*) as total_tasks, 
                   COUNT(CASE WHEN t.is_completed = TRUE THEN 1 END) as completed_tasks
            FROM tasks t
            WHERE t.project_id = :project_id
            AND (
                EXISTS (
                    SELECT 1 FROM concepts c 
                    JOIN days d ON c.day_id = d.day_id 
                    WHERE d.day_number = :day_number AND c.concept_id = t.concept_id
                )
                OR EXISTS (
                    SELECT 1 FROM subconcepts sc
                    JOIN concepts c ON sc.concept_id = c.concept_id
                    JOIN days d ON c.day_id = d.day_id
                    WHERE d.day_number = :day_number AND sc.subconcept_id = t.subconcept_id
                )
            )
        """), {'project_id': project_id, 'day_number': day_number})
        
        task_counts = result.fetchone()
        total_tasks = task_counts[0] if task_counts else 0
        completed_tasks = task_counts[1] if task_counts else 0
        
        if total_tasks == 0:
            print(f"❌ No tasks found for Day {day_number}")
            return False
            
        if completed_tasks < total_tasks:
            print(f"❌ Cannot mark Day {day_number} as completed: Only {completed_tasks}/{total_tasks} tasks completed")
            return False
            
        print(f"✅ Day {day_number}: All {completed_tasks}/{total_tasks} tasks completed!")
    
    # All tasks verified/completed - mark day as completed
    await session.execute(text("""
        UPDATE days 
        SET is_completed = TRUE 
        WHERE project_id = :project_id AND day_number = :day_number
    """), {'project_id': project_id, 'day_number': day_number})
    
    await session.commit()
    print(f"✅ Marked Day {day_number} as completed for project {project_id}")
    
    # Try to unlock next day
    await unlock_next_day(session, project_id, day_number)
    
    # If next day exists and hasn't generated content yet, mark content_generation_started for visibility
    try:
        await session.execute(text(
            """
            UPDATE days
            SET content_generation_started = TRUE
            WHERE project_id = :project_id AND day_number = :next_day
            """
        ), {'project_id': project_id, 'next_day': day_number + 1})
    except Exception:
        pass

    return True

async def get_project_days(session: AsyncSession, project_id: int) -> List[Dict[str, Any]]:
    """
    Get all days for a project with their status
    
    Args:
        session: Database session
        project_id: ID of the project
    
    Returns:
        List of day dictionaries with status information
    """
    result = await session.execute(text("""
        SELECT day_id, project_id, day_number, day_external_id, name, description, 
               is_unlocked, is_completed, "order"
        FROM days 
        WHERE project_id = :project_id 
        ORDER BY day_number
    """), {'project_id': project_id})
    
    days = []
    for row in result.fetchall():
        day_dict = {
            'day_id': row[0],
            'project_id': row[1],
            'day_number': row[2],
            'day_external_id': row[3],
            'name': row[4],
            'description': row[5],
            'is_unlocked': row[6],
            'is_completed': row[7],
            'order': row[8]
        }
        days.append(day_dict)
    
    return days

async def get_current_day(session: AsyncSession, project_id: int) -> Dict[str, Any]:
    """
    Get the current active day (first unlocked, not completed day)
    
    Args:
        session: Database session
        project_id: ID of the project
    
    Returns:
        Dictionary with current day information or None if no active day
    """
    result = await session.execute(text("""
        SELECT day_id, project_id, day_number, day_external_id, name, description, 
               is_unlocked, is_completed, "order"
        FROM days 
        WHERE project_id = :project_id 
              AND is_unlocked = TRUE 
              AND is_completed = FALSE
        ORDER BY day_number
        LIMIT 1
    """), {'project_id': project_id})
    
    row = result.fetchone()
    if not row:
        return None
    
    return {
        'day_id': row[0],
        'project_id': row[1],
        'day_number': row[2],
        'day_external_id': row[3],
        'name': row[4],
        'description': row[5],
        'is_unlocked': row[6],
        'is_completed': row[7],
        'order': row[8]
    } 

async def verify_day0_repository(session: AsyncSession, project_id: int, repo_url: str) -> Dict[str, Any]:
    """
    Verify Day 0 GitHub repository and unlock Day 1 if successful
    
    Args:
        session: Database session
        project_id: ID of the project
        repo_url: GitHub repository URL provided by user
    
    Returns:
        Dictionary with verification result
    """
    import requests
    import os
    
    try:
        # Extract username and repo name from URL
        # Expected format: https://github.com/username/repo-name
        if not repo_url.startswith('https://github.com/'):
            return {
                'success': False,
                'error': 'Invalid GitHub URL format. Must be: https://github.com/username/repo-name'
            }
        
        parts = repo_url.replace('https://github.com/', '').strip('/').split('/')
        if len(parts) != 2:
            return {
                'success': False,
                'error': 'Invalid GitHub URL format. Must be: https://github.com/username/repo-name'
            }
        
        username, repo_name = parts
        
        # Check if repo name ends with -gitguide
        if not repo_name.endswith('-gitguide'):
            return {
                'success': False,
                'error': 'Repository name must end with "-gitguide"'
            }
        
        # Use GitHub API to verify repository exists
        github_token = os.getenv('GITHUB_ACCESS_TOKEN')
        headers = {}
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        api_url = f'https://api.github.com/repos/{username}/{repo_name}'
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            return {
                'success': False,
                'error': f'Repository "{username}/{repo_name}" not found on GitHub'
            }
        elif response.status_code != 200:
            return {
                'success': False,
                'error': f'Failed to verify repository (Status: {response.status_code})'
            }
        
        repo_data = response.json()
        
        # Update Day 0 with verification
        # Do NOT mark day completed or unlock Day 1 here.
        # Task-level verification endpoints will mark tasks verified and trigger unlocks when ALL are done.
        await session.execute(text("""
            UPDATE days 
            SET verification_repo_url = :repo_url, is_verified = TRUE
            WHERE project_id = :project_id AND day_number = 0
        """), {'project_id': project_id, 'repo_url': repo_url})
        
        await session.commit()
        
        print(f"✅ Day 0 verified for project {project_id} (no auto-unlock; will unlock after all Day 0 tasks verified)")
        
        return {
            'success': True,
            'message': 'Repository verified successfully! Day 1 is now unlocked.',
            'repo_info': {
                'name': repo_data.get('name'),
                'description': repo_data.get('description'),
                'private': repo_data.get('private'),
                'created_at': repo_data.get('created_at')
            }
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Failed to connect to GitHub API: {str(e)}'
        }
    except Exception as e:
        await session.rollback()
        return {
            'success': False,
            'error': f'Verification failed: {str(e)}'
        }

async def get_day0_verification_status(session: AsyncSession, project_id: int) -> Dict[str, Any]:
    """
    Get Day 0 verification status for a project
    
    Args:
        session: Database session
        project_id: ID of the project
    
    Returns:
        Dictionary with Day 0 verification status
    """
    result = await session.execute(text("""
        SELECT day_id, requires_verification, verification_repo_url, is_verified, is_completed
        FROM days 
        WHERE project_id = :project_id AND day_number = 0
    """), {'project_id': project_id})
    
    row = result.fetchone()
    if not row:
        return {
            'exists': False,
            'message': 'Day 0 not found for this project'
        }
    
    return {
        'exists': True,
        'day_id': row[0],
        'requires_verification': row[1],
        'verification_repo_url': row[2],
        'is_verified': row[3],
        'is_completed': row[4]
    } 

async def create_day0_concepts_and_tasks(session: AsyncSession, project_id: int) -> None:
    """
    Create fixed Day 0 concepts and tasks for GitHub setup
    These are the same for every project
    """
    from sqlalchemy import text
    
    # Get the Day 0 ID
    result = await session.execute(text("""
        SELECT day_id FROM days 
        WHERE project_id = :project_id AND day_number = 0
    """), {'project_id': project_id})
    
    day0_id = result.scalar_one_or_none()
    if not day0_id:
        print(f"❌ Day 0 not found for project {project_id}")
        return
    
    print(f"📝 Creating Day 0 concepts and tasks for project {project_id}")
    
    # Day 0 Concepts and Tasks Data
    concepts_data = [
        {
            'concept_id': f"concept-day0-1-{project_id}",
            'title': "What is GitHub and Why Use It?",
            'description': """**GitHub** is a cloud-based platform that hosts Git repositories and provides collaboration tools for developers.

**Why GitHub is Essential:**
- 🌍 **Version Control**: Track changes to your code over time
- 👥 **Collaboration**: Work with others on the same project
- 📁 **Code Storage**: Store your code safely in the cloud
- 🔍 **Portfolio**: Showcase your projects to potential employers
- 🔧 **Project Management**: Issues, pull requests, and project boards
- 📚 **Open Source**: Contribute to and learn from millions of projects

**Key Benefits:**
- **Backup**: Your code is safely stored online
- **History**: See exactly what changed and when
- **Branching**: Work on features without breaking main code
- **Community**: Connect with millions of developers worldwide

Whether you're building websites, mobile apps, or any software project, GitHub is the industry standard for code management and collaboration.""",
            'order': 1,
            'tasks': [
                {
                    'task_id': f"task-day0-1-{project_id}",
                    'title': "Create GitHub Account & Verify Profile",
                    'description': """**Your First Step into the Developer World!**

Create your GitHub account and verify your profile to join millions of developers worldwide.

**Steps:**
1. 🌐 Go to [github.com](https://github.com)
2. 🖊️ Click "Sign up" and create your account
3. ✉️ Verify your email address
4. 📝 Complete your profile (add a profile picture and bio)
5. 🔗 Copy your profile URL (e.g., https://github.com/yourusername)
6. 📋 Paste it below and click "Verify Profile"

**Tips for a Great Profile:**
- Use a professional username (you'll use this for years!)
- Add a clear profile picture
- Write a brief bio about your interests
- Consider adding your location and website

**Why This Matters:**
Your GitHub profile is like your developer business card. Employers, collaborators, and the community will see this when they discover your work.""",
                    'order': 1,
                    'verification_type': 'github_profile',
                    'is_completed': False
                }
            ]
        },
        {
            'concept_id': f"concept-day0-2-{project_id}",
            'title': "Understanding Repositories",
            'description': """A **repository** (or "repo") is like a project folder that contains all your code, files, and version history.

**What's in a Repository:**
- 📁 **Files & Folders**: Your actual code and project files
- 📝 **README.md**: Documentation explaining your project
- 📜 **Commit History**: Record of all changes made over time
- 🌳 **Branches**: Different versions of your project
- ⚙️ **Settings**: Repository configuration and permissions

**Types of Repositories:**
- 🔓 **Public**: Anyone can see your code (great for portfolios!)
- 🔒 **Private**: Only you and invited collaborators can access

**Repository Structure:**
```
my-awesome-project/
├── README.md          # Project documentation
├── src/              # Source code folder
├── docs/             # Additional documentation
├── .gitignore        # Files to ignore in version control
└── LICENSE           # Project license
```

**Why Repositories Matter:**
- **Organization**: Keep your project files structured
- **Collaboration**: Multiple people can work on the same project
- **Backup**: Your code is safely stored with full history
- **Sharing**: Easy to share your work with others

Think of a repository as your project's home on GitHub - everything related to that project lives there!""",
            'order': 2,
            'tasks': [
                {
                    'task_id': f"task-day0-2-{project_id}",
                    'title': "Create Your Practice Repository",
                    'description': """**Create Your Own Learning Repository!**

Now it's time to create your own repository where you'll practice and apply everything you learn.

**Steps:**
1. 🔗 Go to [github.com/new](https://github.com/new) (or click "+" → "New repository")
2. 📝 Repository name: `[your-project-name]-gitguide`
   - For example: `tic-tac-toe-gitguide` or `weather-app-gitguide`
3. 📋 Add a description: "Learning repository for [project name] with GitGuide"
4. ✅ Make it **Public** (so you can showcase your progress!)
5. ✅ Check "Add a README file"
6. 🎯 Click "Create repository"
7. 🔗 Copy the repository URL (e.g., https://github.com/yourusername/project-gitguide)
8. 📋 Paste it below and click "Verify Repository"

**Important Naming Convention:**
Your repository MUST end with `-gitguide` to be accepted by our verification system.

**Why This Repository Matters:**
This will be your practice playground where you'll:
- Apply concepts you learn
- Experiment with code
- Track your learning progress
- Build something you can show to others

**Pro Tip:** 
Choose a name related to the project you're learning about. This makes it clear what the repository is for and helps with organization!""",
                    'order': 1,
                    'verification_type': 'repository_creation',
                    'is_completed': False
                }
            ]
        },
        {
            'concept_id': f"concept-day0-3-{project_id}",
            'title': "Git Clone and Making Your First Commit",
            'description': """**Git Clone** downloads a repository to your computer so you can work on it locally.

**What is Git Clone?**
- 📥 **Download**: Gets the entire repository and its history
- 🔗 **Connection**: Links your local copy to the remote repository
- 📁 **Local Copy**: Creates a folder on your computer with all project files

**The Git Workflow:**
1. **Clone**: Download repository to your computer
2. **Edit**: Make changes to files locally
3. **Stage**: Select which changes to include
4. **Commit**: Save changes with a descriptive message
5. **Push**: Upload your changes back to GitHub

**What is a Commit?**
A commit is like a "save point" in your project:
- 📸 **Snapshot**: Records the state of your files at a specific time
- 💬 **Message**: Describes what changes were made
- 🏷️ **ID**: Unique identifier for that specific change
- 👤 **Author**: Records who made the change and when

**Commit Message Best Practices:**
- ✅ "Add user login functionality"
- ✅ "Fix navigation bug on mobile"
- ✅ "Update README with installation instructions"
- ❌ "Fixed stuff" (too vague)
- ❌ "WIP" (not descriptive)

**Why This Workflow Matters:**
- **Safety**: You can always go back to previous versions
- **Collaboration**: Others can see exactly what you changed
- **Documentation**: Commit history tells the story of your project
- **Backup**: Your changes are safely stored on GitHub

**The README.md File:**
- 📄 Written in Markdown format
- 🏠 First thing people see when they visit your repository
- 📖 Explains what your project does and how to use it
- 📝 Should include project description, installation steps, and usage examples""",
            'order': 3,
            'tasks': [
                {
                    'task_id': f"task-day0-3-{project_id}",
                    'title': "Clone, Edit, and Push Your First Commit",
                    'description': """**Make Your First Real Code Change!**

Time to experience the full Git workflow - clone your repository, make a change, and push it back to GitHub.

**Steps:**

**1. Clone Your Repository** 🔽
- Open your IDE (VS Code, PyCharm, etc.) or terminal
- Run: `git clone [your-repository-url]`
- Navigate into the folder: `cd [repository-name]`

**2. Edit the README.md File** ✏️
Add this content to your README.md:
```markdown
# [Your Project Name] - GitGuide Learning Journey

## About This Repository
This repository is part of my learning journey with GitGuide. I'm learning to build [describe the project] while mastering Git and GitHub workflows.

## Learning Progress
- ✅ Day 0: GitHub fundamentals and repository setup
- 🔄 Day 1-14: Coming soon...

## What I'm Learning
- Git version control
- GitHub collaboration
- [Add specific technologies for your project]

## Connect With Me
- GitHub: [your-github-profile-url]
- [Add other social links if you want]

---
*This project is part of the GitGuide learning platform.*
```

**3. Commit Your Changes** 💾
```bash
git add README.md
git commit -m "Update README with project information and learning goals"
git push origin main
```

**4. Verify Your Commit** ✅
- Go to your GitHub repository page
- You should see your updated README.md
- Click "Verify Commit" below to confirm your push

**What You're Learning:**
- How to clone repositories to your computer
- Basic Git commands (add, commit, push)
- Markdown formatting for documentation
- The importance of clear commit messages

**Troubleshooting:**
- If `git push` asks for credentials, you may need to set up authentication
- Use GitHub Desktop or configure SSH keys for easier authentication
- Make sure you're in the correct directory when running commands""",
                    'order': 1,
                    'verification_type': 'commit_verification',
                    'is_completed': False
                }
            ]
        }
    ]
    
    # Insert concepts and tasks
    for concept_data in concepts_data:
        # Insert concept
        await session.execute(text("""
            INSERT INTO concepts (day_id, project_id, concept_external_id, title, description, is_unlocked, is_completed, "order")
            VALUES (:day_id, :project_id, :concept_external_id, :title, :description, :is_unlocked, :is_completed, :order)
        """), {
            'day_id': day0_id,
            'project_id': project_id,  # Add project_id here
            'concept_external_id': concept_data['concept_id'],
            'title': concept_data['title'],
            'description': concept_data['description'],
            'is_unlocked': True,  # Day 0 concepts are always unlocked
            'is_completed': False,
            'order': concept_data['order']
        })
        
        # Get the concept ID we just inserted
        concept_result = await session.execute(text("""
            SELECT concept_id FROM concepts 
            WHERE concept_external_id = :concept_external_id
        """), {'concept_external_id': concept_data['concept_id']})
        
        concept_id = concept_result.scalar_one()
        
        # Insert tasks for this concept
        for task_data in concept_data['tasks']:
            await session.execute(text("""
                INSERT INTO tasks (concept_id, project_id, task_external_id, title, description, status, is_completed, is_unlocked, "order", verification_type)
                VALUES (:concept_id, :project_id, :task_external_id, :title, :description, :status, :is_completed, :is_unlocked, :order, :verification_type)
                RETURNING task_id
            """), {
                'concept_id': concept_id,
                'project_id': project_id,
                'task_external_id': task_data['task_id'],
                'title': task_data['title'],
                'description': task_data['description'],
                'status': 'not_started',  # Default status for Day 0 tasks
                'is_completed': task_data['is_completed'],
                'is_unlocked': True,  # Day 0 tasks are always unlocked
                'order': task_data['order'],
                'verification_type': task_data['verification_type']
            })
    
    await session.commit()
    print(f"✅ Created Day 0 concepts and tasks for project {project_id}") 

async def verify_github_profile(session: AsyncSession, project_id: int, task_id: int, profile_url: str) -> Dict[str, Any]:
    """
    Verify GitHub profile URL for Day 0 Task 1
    
    Args:
        session: Database session
        project_id: ID of the project
        task_id: ID of the task
        profile_url: GitHub profile URL provided by user
    
    Returns:
        Dictionary with verification result
    """
    import requests
    import os
    import json
    
    try:
        # Extract username from URL
        # Expected format: https://github.com/username
        if not profile_url.startswith('https://github.com/'):
            return {
                'success': False,
                'error': 'Invalid GitHub profile URL format. Must be: https://github.com/username'
            }
        
        # Remove trailing slash and extract username
        username = profile_url.replace('https://github.com/', '').strip('/')
        
        if '/' in username or not username:
            return {
                'success': False,
                'error': 'Invalid GitHub profile URL format. Must be: https://github.com/username'
            }
        
        # Use GitHub API to verify profile exists
        github_token = os.getenv('GITHUB_ACCESS_TOKEN')
        headers = {}
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        api_url = f'https://api.github.com/users/{username}'
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            return {
                'success': False,
                'error': f'GitHub user "{username}" not found'
            }
        elif response.status_code != 200:
            return {
                'success': False,
                'error': f'Failed to verify GitHub profile (Status: {response.status_code})'
            }
        
        user_data = response.json()
        
        # Update task with verification
        await session.execute(text("""
            UPDATE tasks 
            SET verification_data = :verification_data, is_verified = TRUE, is_completed = TRUE
            WHERE task_id = :task_id
        """), {
            'task_id': task_id,
            'verification_data': json.dumps({
                'profile_url': profile_url,
                'username': username,
                'verified_at': None  # Will be set by database
            })
        })
        
        await session.commit()
        
        print(f"✅ GitHub profile verified for task {task_id}")
        
        # Check if this verification unlocks the next day
        day_unlocked = await check_and_unlock_next_day_after_verification(session, project_id, task_id)
        
        return {
            'success': True,
            'message': f'GitHub profile verified successfully!' + (' Day unlocked!' if day_unlocked else ''),
            'profile_info': {
                'username': user_data.get('login'),
                'name': user_data.get('name'),
                'bio': user_data.get('bio'),
                'public_repos': user_data.get('public_repos'),
                'followers': user_data.get('followers'),
                'avatar_url': user_data.get('avatar_url')
            },
            'day_unlocked': day_unlocked
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Failed to connect to GitHub API: {str(e)}'
        }
    except Exception as e:
        await session.rollback()
        return {
            'success': False,
            'error': f'Verification failed: {str(e)}'
        }

async def verify_repository_creation_task(session: AsyncSession, project_id: int, task_id: int, repo_url: str) -> Dict[str, Any]:
    """
    Verify repository creation for Day 0 Task 2
    Similar to verify_day0_repository but for task-level verification
    """
    import requests
    import os
    import json
    
    try:
        # Reuse the existing repository verification logic
        result = await verify_day0_repository(session, project_id, repo_url)
        
        if result['success']:
            # Also update the specific task
            await session.execute(text("""
                UPDATE tasks 
                SET verification_data = :verification_data, is_verified = TRUE, is_completed = TRUE
                WHERE task_id = :task_id
            """), {
                'task_id': task_id,
                'verification_data': json.dumps({
                    'repo_url': repo_url,
                    'verified_at': None  # Will be set by database
                })
            })
            
            await session.commit()
            print(f"✅ Repository creation verified for task {task_id}")
            
            # Check if this verification unlocks the next day
            day_unlocked = await check_and_unlock_next_day_after_verification(session, project_id, task_id)
            
            # Add day unlock info to result
            result['day_unlocked'] = day_unlocked
            if day_unlocked:
                result['message'] += ' Day unlocked!'
        
        return result
        
    except Exception as e:
        await session.rollback()
        return {
            'success': False,
            'error': f'Repository verification failed: {str(e)}'
        }

async def verify_commit_task(session: AsyncSession, project_id: int, task_id: int) -> Dict[str, Any]:
    """
    Verify that user made a commit to their repository for Day 0 Task 3
    
    Args:
        session: Database session
        project_id: ID of the project
        task_id: ID of the task
    
    Returns:
        Dictionary with verification result
    """
    import requests
    import os
    import json
    from datetime import datetime, timedelta
    
    try:
        # Get the repository URL from Day 0 verification
        result = await session.execute(text("""
            SELECT verification_repo_url FROM days 
            WHERE project_id = :project_id AND day_number = 0
        """), {'project_id': project_id})
        
        repo_url = result.scalar_one_or_none()
        if not repo_url:
            return {
                'success': False,
                'error': 'Repository not found. Please complete repository verification first.'
            }
        
        # Extract username and repo name from URL
        parts = repo_url.replace('https://github.com/', '').strip('/').split('/')
        if len(parts) != 2:
            return {
                'success': False,
                'error': 'Invalid repository URL format'
            }
        
        username, repo_name = parts
        
        # Use GitHub API to get recent commits
        github_token = os.getenv('GITHUB_ACCESS_TOKEN')
        headers = {}
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        # Get commits from the last hour (to check for recent activity)
        since_time = datetime.utcnow() - timedelta(hours=24)  # 24 hours to be more lenient
        api_url = f'https://api.github.com/repos/{username}/{repo_name}/commits'
        params = {
            'since': since_time.isoformat() + 'Z',
            'per_page': 10
        }
        
        response = requests.get(api_url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 404:
            return {
                'success': False,
                'error': f'Repository "{username}/{repo_name}" not found or is private'
            }
        elif response.status_code != 200:
            return {
                'success': False,
                'error': f'Failed to fetch commits (Status: {response.status_code})'
            }
        
        commits = response.json()
        
        if not commits:
            return {
                'success': False,
                'error': 'No recent commits found. Please make sure you have pushed your changes to GitHub.'
            }
        
        # Find the most recent commit
        latest_commit = commits[0]
        commit_message = latest_commit.get('commit', {}).get('message', '')
        commit_date = latest_commit.get('commit', {}).get('author', {}).get('date', '')
        commit_sha = latest_commit.get('sha', '')
        
        # Update task with verification
        await session.execute(text("""
            UPDATE tasks 
            SET verification_data = :verification_data, is_verified = TRUE, is_completed = TRUE
            WHERE task_id = :task_id
        """), {
            'task_id': task_id,
            'verification_data': json.dumps({
                'repo_url': repo_url,
                'latest_commit_sha': commit_sha,
                'commit_message': commit_message,
                'commit_date': commit_date,
                'verified_at': None  # Will be set by database
            })
        })
        
        await session.commit()
        
        print(f"✅ Commit verified for task {task_id}")
        
        # Check if this verification unlocks the next day
        day_unlocked = await check_and_unlock_next_day_after_verification(session, project_id, task_id)
        
        return {
            'success': True,
            'message': 'Commit verified successfully! Your changes have been pushed to GitHub.' + (' Day unlocked!' if day_unlocked else ''),
            'commit_info': {
                'message': commit_message,
                'date': commit_date,
                'sha': commit_sha[:8],  # Short SHA for display
                'url': f'{repo_url}/commit/{commit_sha}'
            },
            'day_unlocked': day_unlocked
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Failed to connect to GitHub API: {str(e)}'
        }
    except Exception as e:
        await session.rollback()
        return {
            'success': False,
            'error': f'Commit verification failed: {str(e)}'
        } 

async def check_and_unlock_next_day_after_verification(session: AsyncSession, project_id: int, task_id: int) -> bool:
    """
    Check if all tasks in the current day are verified and unlock next day/task if so
    Called after a task is verified
    
    Args:
        session: Database session  
        project_id: ID of the project
        task_id: ID of the task that was just verified
    
    Returns:
        True if next day was unlocked, False otherwise
    """
    try:
        # Get the day number for this task
        result = await session.execute(text("""
            SELECT d.day_number 
            FROM tasks t
            JOIN concepts c ON t.concept_id = c.concept_id
            JOIN days d ON c.day_id = d.day_id
            WHERE t.task_id = :task_id
        """), {'task_id': task_id})
        
        day_number = result.scalar_one_or_none()
        if day_number is None:
            print(f"❌ Could not find day number for task {task_id}")
            return False
        
        print(f"📋 Task {task_id} belongs to Day {day_number}")
        
        # For Day 0: Unlock next task in sequence
        if day_number == 0:
            await unlock_next_day0_task(session, project_id, task_id)
        
        print(f"📋 Checking if Day {day_number + 1} should be unlocked")
        
        # Try to unlock the next day (this will check if all tasks are verified)
        return await unlock_next_day(session, project_id, day_number)
        
    except Exception as e:
        print(f"❌ Error checking day unlock after task verification: {str(e)}")
        return False

async def check_and_unlock_next_day_after_task_completion(session: AsyncSession, project_id: int, task_id: int) -> bool:
    """
    Check if all tasks in the current day are completed and unlock next day if so
    Called after a regular task (Days 1-14) is marked as completed
    
    Args:
        session: Database session  
        project_id: ID of the project
        task_id: ID of the task that was just completed
    
    Returns:
        True if next day was unlocked, False otherwise
    """
    try:
        # Get the day number for this task
        result = await session.execute(text("""
            SELECT d.day_number 
            FROM tasks t
            JOIN concepts c ON t.concept_id = c.concept_id
            JOIN days d ON c.day_id = d.day_id
            WHERE t.task_id = :task_id
        """), {'task_id': task_id})
        
        day_number = result.scalar_one_or_none()
        if day_number is None:
            print(f"❌ Could not find day number for task {task_id}")
            return False
        
        print(f"📋 Task {task_id} belongs to Day {day_number}")
        
        # For regular days (1-14), check if all tasks in the day are completed
        if day_number > 0:
            # Try to unlock the next day (this will check if all tasks are completed)
            day_unlocked = await unlock_next_day(session, project_id, day_number)
            
            # Also try to mark current day as completed if all tasks are done
            if day_unlocked:
                try:
                    await mark_day_completed(session, project_id, day_number)
                except Exception as e:
                    print(f"⚠️ Failed to mark day {day_number} as completed: {str(e)}")
            
            return day_unlocked
        else:
            print(f"📋 Day {day_number} is Day 0, using verification logic instead")
            return False
        
    except Exception as e:
        print(f"❌ Error checking day unlock after task completion: {str(e)}")
        return False

async def unlock_next_day0_task(session: AsyncSession, project_id: int, completed_task_id: int) -> bool:
    """
    Unlock the next task in Day 0 sequence after completing current task
    
    Args:
        session: Database session
        project_id: ID of the project  
        completed_task_id: ID of the task that was just completed
    
    Returns:
        True if next task was unlocked, False otherwise
    """
    try:
        # Define the verification sequence for Day 0
        verification_sequence = ['github_profile', 'repository_creation', 'commit_verification']
        
        # Get the verification type of the completed task
        result = await session.execute(text("""
            SELECT verification_type FROM tasks 
            WHERE task_id = :task_id AND project_id = :project_id
        """), {'task_id': completed_task_id, 'project_id': project_id})
        
        completed_verification_type = result.scalar_one_or_none()
        if not completed_verification_type:
            print(f"❌ Could not find verification type for task {completed_task_id}")
            return False
        
        # Find current position in sequence
        if completed_verification_type not in verification_sequence:
            print(f"❌ Unknown verification type: {completed_verification_type}")
            return False
        
        current_index = verification_sequence.index(completed_verification_type)
        next_index = current_index + 1
        
        # If this is the last task, no next task to unlock
        if next_index >= len(verification_sequence):
            print(f"✅ Task {completed_task_id} is the last Day 0 task")
            return False
        
        next_verification_type = verification_sequence[next_index]
        
        # Unlock the next task
        result = await session.execute(text("""
            UPDATE tasks 
            SET is_unlocked = TRUE 
            WHERE project_id = :project_id 
            AND verification_type = :next_verification_type
            AND is_unlocked = FALSE
        """), {
            'project_id': project_id, 
            'next_verification_type': next_verification_type
        })
        
        await session.commit()
        
        print(f"✅ Unlocked next Day 0 task: {next_verification_type}")
        return True
        
    except Exception as e:
        print(f"❌ Error unlocking next Day 0 task: {str(e)}")
        await session.rollback()
        return False 

async def verify_file_creation_task(session: AsyncSession, project_id: int, task_id: int, username: str, repo_name: str) -> Dict[str, Any]:
    """
    Verify that specific files were created in the repository
    
    Args:
        session: Database session
        project_id: ID of the project
        task_id: ID of the task
        username: GitHub username
        repo_name: GitHub repository name
    
    Returns:
        Dictionary with verification result
    """
    import requests
    import os
    import json
    
    try:
        # Get task details to see what files should be checked
        result = await session.execute(text("""
            SELECT description, verification_data FROM tasks 
            WHERE task_id = :task_id
        """), {'task_id': task_id})
        
        task_data = result.fetchone()
        if not task_data:
            return {
                'success': False,
                'error': 'Task not found'
            }
        
        description = task_data[0]
        verification_data = task_data[1]
        
        # Parse verification data to get expected files
        expected_files = []
        if verification_data:
            try:
                data = json.loads(verification_data)
                expected_files = data.get('files', [])
            except:
                # If no JSON data, try to extract from description
                if 'README.md' in description:
                    expected_files = ['README.md']
                elif '.py' in description:
                    expected_files = ['main.py', 'app.py', '*.py']
                elif '.js' in description:
                    expected_files = ['index.js', 'app.js', '*.js']
        
        if not expected_files:
            # Default check for common files
            expected_files = ['README.md']
        
        # Use GitHub API to check repository contents
        github_token = os.getenv('GITHUB_ACCESS_TOKEN')
        headers = {}
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        api_url = f'https://api.github.com/repos/{username}/{repo_name}/contents'
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            return {
                'success': False,
                'error': 'Repository not found or not accessible'
            }
        elif response.status_code != 200:
            return {
                'success': False,
                'error': f'Failed to access repository contents (Status: {response.status_code})'
            }
        
        contents = response.json()
        found_files = [item['name'] for item in contents if item['type'] == 'file']
        
        # Check if expected files exist
        verified_files = []
        missing_files = []
        
        for expected_file in expected_files:
            if expected_file in found_files:
                verified_files.append(expected_file)
            elif expected_file.startswith('*'):
                # Wildcard check
                extension = expected_file[1:]
                matching_files = [f for f in found_files if f.endswith(extension)]
                if matching_files:
                    verified_files.extend(matching_files)
                else:
                    missing_files.append(expected_file)
            else:
                missing_files.append(expected_file)
        
        if missing_files:
            return {
                'success': False,
                'error': f'Missing required files: {", ".join(missing_files)}'
            }
        
        # Update task verification
        await session.execute(text("""
            UPDATE tasks 
            SET verification_data = :verification_data, is_verified = TRUE, is_completed = TRUE
            WHERE task_id = :task_id
        """), {
            'task_id': task_id,
            'verification_data': json.dumps({
                'expected_files': expected_files,
                'found_files': verified_files,
                'repository': f'{username}/{repo_name}',
                'verified_at': None  # Will be set by database
            })
        })
        
        await session.commit()
        
        print(f"✅ File creation verified for task {task_id}: {verified_files}")
        
        return {
            'success': True,
            'message': f'File creation verified successfully! Found: {", ".join(verified_files)}',
            'file_info': {
                'expected_files': expected_files,
                'found_files': verified_files,
                'repository': f'{username}/{repo_name}'
            }
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Failed to connect to GitHub API: {str(e)}'
        }
    except Exception as e:
        await session.rollback()
        return {
            'success': False,
            'error': f'File verification failed: {str(e)}'
        }

async def verify_readme_update_task(session: AsyncSession, project_id: int, task_id: int, username: str, repo_name: str) -> Dict[str, Any]:
    """
    Verify that README.md was updated with specific content
    
    Args:
        session: Database session
        project_id: ID of the project
        task_id: ID of the task
        username: GitHub username
        repo_name: GitHub repository name
    
    Returns:
        Dictionary with verification result
    """
    import requests
    import os
    import json
    import base64
    
    try:
        # Use GitHub API to get README content
        github_token = os.getenv('GITHUB_ACCESS_TOKEN')
        headers = {}
        if github_token:
            headers['Authorization'] = f'token {github_token}'
        
        api_url = f'https://api.github.com/repos/{username}/{repo_name}/contents/README.md'
        response = requests.get(api_url, headers=headers, timeout=10)
        
        if response.status_code == 404:
            return {
                'success': False,
                'error': 'README.md not found in repository'
            }
        elif response.status_code != 200:
            return {
                'success': False,
                'error': f'Failed to access README.md (Status: {response.status_code})'
            }
        
        readme_data = response.json()
        
        # Decode base64 content
        content = base64.b64decode(readme_data['content']).decode('utf-8')
        
        # Check if README has meaningful content (not just default)
        required_content = [
            'project',
            'description',
            'installation',
            'usage'
        ]
        
        content_lower = content.lower()
        found_sections = []
        
        for section in required_content:
            if section in content_lower:
                found_sections.append(section)
        
        # README must have at least 2 sections and be longer than 100 characters
        if len(found_sections) < 2 or len(content.strip()) < 100:
            return {
                'success': False,
                'error': f'README.md needs more content. Found: {", ".join(found_sections)}. Add project description, installation, and usage instructions.'
            }
        
        # Update task verification
        await session.execute(text("""
            UPDATE tasks 
            SET verification_data = :verification_data, is_verified = TRUE, is_completed = TRUE
            WHERE task_id = :task_id
        """), {
            'task_id': task_id,
            'verification_data': json.dumps({
                'readme_length': len(content),
                'found_sections': found_sections,
                'repository': f'{username}/{repo_name}',
                'verified_at': None  # Will be set by database
            })
        })
        
        await session.commit()
        
        print(f"✅ README update verified for task {task_id}")
        
        return {
            'success': True,
            'message': f'README.md verified successfully! Found sections: {", ".join(found_sections)}',
            'readme_info': {
                'length': len(content),
                'sections': found_sections,
                'repository': f'{username}/{repo_name}'
            }
        }
        
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f'Failed to connect to GitHub API: {str(e)}'
        }
    except Exception as e:
        await session.rollback()
        return {
            'success': False,
            'error': f'README verification failed: {str(e)}'
        }

async def get_day_verification_status(session: AsyncSession, project_id: int, day_number: int) -> Dict[str, Any]:
    """
    Get detailed verification status for a specific day
    
    Args:
        session: Database session
        project_id: ID of the project
        day_number: Day number to check
    
    Returns:
        Dictionary with verification status details
    """
    try:
        if day_number == 0:
            # For Day 0: Check verification tasks
            result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN t.is_verified = TRUE THEN 1 END) as verified_tasks,
                    COUNT(CASE WHEN t.is_completed = TRUE THEN 1 END) as completed_tasks
                FROM tasks t
                JOIN concepts c ON t.concept_id = c.concept_id
                JOIN days d ON c.day_id = d.day_id
                WHERE d.project_id = :project_id AND d.day_number = :day_number
                AND t.verification_type IS NOT NULL
            """), {'project_id': project_id, 'day_number': day_number})
            
            counts = result.fetchone()
            total = counts[0] if counts else 0
            verified = counts[1] if counts else 0
            completed = counts[2] if counts else 0
            
            can_unlock_next = verified == total and total > 0
            
            return {
                'day_number': day_number,
                'total_tasks': total,
                'verified_tasks': verified,
                'completed_tasks': completed,
                'all_verified': can_unlock_next,
                'verification_type': 'verification_required',
                'progress_percentage': (verified / total * 100) if total > 0 else 0
            }
            
        else:
            # For Days 1-14: Check regular task completion
            result = await session.execute(text("""
                SELECT 
                    COUNT(*) as total_tasks,
                    COUNT(CASE WHEN t.is_completed = TRUE THEN 1 END) as completed_tasks
                FROM tasks t
                WHERE t.project_id = :project_id
                AND EXISTS (
                    SELECT 1 FROM concepts c 
                    JOIN days d ON c.day_id = d.day_id 
                    WHERE c.concept_id = t.concept_id 
                    AND d.day_number = :day_number
                )
            """), {'project_id': project_id, 'day_number': day_number})
            
            counts = result.fetchone()
            total = counts[0] if counts else 0
            completed = counts[1] if counts else 0
            
            can_unlock_next = completed == total and total > 0
            
            return {
                'day_number': day_number,
                'total_tasks': total,
                'completed_tasks': completed,
                'verified_tasks': completed,  # For regular days, completed = verified
                'all_verified': can_unlock_next,
                'verification_type': 'completion_required',
                'progress_percentage': (completed / total * 100) if total > 0 else 0
            }
            
    except Exception as e:
        print(f"❌ Error getting verification status for Day {day_number}: {str(e)}")
        return {
            'day_number': day_number,
            'total_tasks': 0,
            'verified_tasks': 0,
            'completed_tasks': 0,
            'all_verified': False,
            'verification_type': 'unknown',
            'progress_percentage': 0,
            'error': str(e)
        } 