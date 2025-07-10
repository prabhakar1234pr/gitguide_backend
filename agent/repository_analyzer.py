import requests
import base64
import json
from urllib.parse import urlparse

async def analyze_repository(repo_url, github_token):
    """
    Analyze a GitHub repository by reading its structure and key files
    
    Args:
        repo_url: GitHub repository URL
        github_token: GitHub access token
        
    Returns:
        dict: Analysis result with files, structure, and metadata
    """
    try:
        # Extract owner and repo name from URL
        owner, repo_name = extract_repo_info(repo_url)
        if not owner or not repo_name:
            return {
                'success': False,
                'error': f"Invalid GitHub URL: {repo_url}"
            }
        
        # Get repository information
        repo_info = await get_repository_info(owner, repo_name, github_token)
        if not repo_info['success']:
            return repo_info
        
        # Get repository file structure
        file_tree = await get_repository_tree(owner, repo_name, github_token)
        if not file_tree['success']:
            return file_tree
        
        # Read important files
        file_contents = await read_important_files(
            owner, repo_name, file_tree['files'], github_token
        )
        
        # Analyze tech stack
        tech_stack = analyze_tech_stack(file_contents, file_tree['files'])
        
        return {
            'success': True,
            'repo_info': repo_info['data'],
            'files': file_contents,
            'file_structure': file_tree['files'],
            'tech_stack': tech_stack,
            'total_files': len(file_tree['files'])
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Repository analysis failed: {str(e)}"
        }

def extract_repo_info(repo_url):
    """Extract owner and repository name from GitHub URL"""
    try:
        if 'github.com' not in repo_url:
            return None, None
            
        # Handle different URL formats
        if repo_url.endswith('.git'):
            repo_url = repo_url[:-4]
            
        parsed = urlparse(repo_url)
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) >= 2:
            return path_parts[0], path_parts[1]
        
        return None, None
    except:
        return None, None

async def get_repository_info(owner, repo_name, github_token):
    """Get basic repository information"""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo_name}"
        headers = {"Authorization": f"token {github_token}"}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'data': {
                    'name': data['name'],
                    'full_name': data['full_name'],
                    'description': data.get('description', ''),
                    'language': data.get('language', ''),
                    'size': data['size'],
                    'stargazers_count': data['stargazers_count'],
                    'topics': data.get('topics', [])
                }
            }
        elif response.status_code == 404:
            return {'success': False, 'error': 'Repository not found'}
        else:
            return {'success': False, 'error': f'GitHub API error: {response.status_code}'}
            
    except Exception as e:
        return {'success': False, 'error': f'Failed to get repository info: {str(e)}'}

async def get_repository_tree(owner, repo_name, github_token):
    """Get the file tree of the repository"""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/main?recursive=1"
        headers = {"Authorization": f"token {github_token}"}
        
        response = requests.get(url, headers=headers)
        
        # Try 'main' branch first, then 'master'
        if response.status_code == 404:
            url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/master?recursive=1"
            response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            tree_data = response.json()
            files = []
            
            for item in tree_data.get('tree', []):
                if item['type'] == 'blob' and is_relevant_file(item['path']):
                    files.append({
                        'path': item['path'],
                        'size': item.get('size', 0),
                        'url': item['url']
                    })
            
            return {
                'success': True,
                'files': files
            }
        else:
            return {'success': False, 'error': f'Failed to get repository tree: {response.status_code}'}
            
    except Exception as e:
        return {'success': False, 'error': f'Failed to get repository tree: {str(e)}'}

def is_relevant_file(file_path):
    """Check if a file is relevant for analysis"""
    # Skip common directories
    skip_dirs = [
        'node_modules/', '.git/', 'dist/', 'build/', '.next/', 
        '__pycache__/', '.pytest_cache/', 'coverage/', 'venv/', 
        'env/', '.env/', 'target/', 'bin/', 'obj/'
    ]
    
    for skip_dir in skip_dirs:
        if skip_dir in file_path:
            return False
    
    # Include relevant file extensions
    relevant_extensions = [
        '.js', '.jsx', '.ts', '.tsx', '.py', '.java', '.cpp', '.c', '.cs',
        '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.dart', '.vue',
        '.html', '.css', '.scss', '.less', '.sql', '.json', '.yml', '.yaml',
        '.md', '.txt', '.toml', '.ini', '.cfg', '.xml'
    ]
    
    # Always include important config files
    important_files = [
        'README.md', 'package.json', 'requirements.txt', 'Cargo.toml',
        'pom.xml', 'build.gradle', 'composer.json', 'Gemfile',
        'setup.py', 'pyproject.toml', 'Dockerfile', 'docker-compose.yml'
    ]
    
    file_name = file_path.split('/')[-1]
    if file_name in important_files:
        return True
    
    return any(file_path.endswith(ext) for ext in relevant_extensions)

async def read_important_files(owner, repo_name, files, github_token):
    """Read content of important files"""
    file_contents = {}
    total_size = 0
    max_total_size = 400000  # ~400KB limit for LLM context
    
    # Prioritize files by importance
    priority_files = []
    regular_files = []
    
    for file in files:
        file_name = file['path'].split('/')[-1]
        if file_name in ['README.md', 'package.json', 'requirements.txt', 'setup.py']:
            priority_files.append(file)
        else:
            regular_files.append(file)
    
    # Read priority files first
    for file in priority_files + regular_files:
        if total_size > max_total_size:
            break
            
        try:
            content = await read_file_content(owner, repo_name, file['path'], github_token)
            if content and len(content) < 50000:  # Skip very large files
                file_contents[file['path']] = content
                total_size += len(content)
        except:
            continue  # Skip files that can't be read
    
    return file_contents

async def read_file_content(owner, repo_name, file_path, github_token):
    """Read the content of a specific file"""
    try:
        url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{file_path}"
        headers = {"Authorization": f"token {github_token}"}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            file_data = response.json()
            if file_data.get('encoding') == 'base64':
                content = base64.b64decode(file_data['content']).decode('utf-8')
                return content
        
        return None
    except:
        return None

def analyze_tech_stack(file_contents, file_list):
    """Analyze the technology stack based on files"""
    tech_stack = {
        'languages': set(),
        'frameworks': set(),
        'tools': set(),
        'databases': set()
    }
    
    # Analyze by file extensions
    for file_info in file_list:
        file_path = file_info['path']
        if file_path.endswith('.js') or file_path.endswith('.jsx'):
            tech_stack['languages'].add('JavaScript')
        elif file_path.endswith('.ts') or file_path.endswith('.tsx'):
            tech_stack['languages'].add('TypeScript')
        elif file_path.endswith('.py'):
            tech_stack['languages'].add('Python')
        elif file_path.endswith('.java'):
            tech_stack['languages'].add('Java')
        elif file_path.endswith('.go'):
            tech_stack['languages'].add('Go')
        elif file_path.endswith('.rs'):
            tech_stack['languages'].add('Rust')
    
    # Analyze package.json for JavaScript frameworks
    if 'package.json' in file_contents:
        try:
            package_data = json.loads(file_contents['package.json'])
            dependencies = {**package_data.get('dependencies', {}), 
                          **package_data.get('devDependencies', {})}
            
            if 'react' in dependencies:
                tech_stack['frameworks'].add('React')
            if 'next' in dependencies:
                tech_stack['frameworks'].add('Next.js')
            if 'vue' in dependencies:
                tech_stack['frameworks'].add('Vue.js')
            if 'express' in dependencies:
                tech_stack['frameworks'].add('Express.js')
            if 'fastapi' in str(dependencies).lower():
                tech_stack['frameworks'].add('FastAPI')
        except:
            pass
    
    # Analyze requirements.txt for Python frameworks
    if 'requirements.txt' in file_contents:
        requirements = file_contents['requirements.txt'].lower()
        if 'django' in requirements:
            tech_stack['frameworks'].add('Django')
        if 'flask' in requirements:
            tech_stack['frameworks'].add('Flask')
        if 'fastapi' in requirements:
            tech_stack['frameworks'].add('FastAPI')
    
    # Convert sets to lists for JSON serialization
    return {
        'languages': list(tech_stack['languages']),
        'frameworks': list(tech_stack['frameworks']),
        'tools': list(tech_stack['tools']),
        'databases': list(tech_stack['databases'])
    } 