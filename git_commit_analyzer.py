"""
Git Commit Analyzer using OpenRouter LLM

Before running this script, set up a virtual environment:
1. Create a virtual environment:
   python -m venv venv
2. Activate the virtual environment:
   - On Windows: venv/Scripts/activate
   - On macOS and Linux: source venv/bin/activate
3. Install the required packages:
   pip install -r requirements.txt
4. Set the OPENROUTER_API_KEY environment variable:
   - On Windows: set OPENROUTER_API_KEY=your_api_key_here
   - On macOS and Linux: export OPENROUTER_API_KEY=your_api_key_here

Usage:
python git_commit_analyzer.py /path/to/your/repo [--num-commits N]
"""

import os
import subprocess
import argparse
import requests
import json

def get_commits(repo_path, num_commits=None):
    """Get the list of commits from the repository."""
    os.chdir(repo_path)
    git_log_cmd = ['git', 'log', '--pretty=format:%H %s']
    if num_commits:
        git_log_cmd.extend(['-n', str(num_commits)])
    result = subprocess.run(git_log_cmd, capture_output=True, text=True)
    commits = result.stdout.strip().split('\n')
    return [{'hash': c.split()[0], 'message': ' '.join(c.split()[1:])} for c in commits]

def summarize_commits(commits, api_key):
    """Summarize the commits using OpenRouter LLM."""
    commit_messages = "\n".join([f"{c['hash'][:7]}: {c['message']}" for c in commits])
    prompt = f"Summarize the following git commits and suggest a single commit message that encompasses all changes:\n\n{commit_messages}"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    data = {
        "model": "openai/gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}]
    }

    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=data)
    response_json = response.json()
    
    return response_json['choices'][0]['message']['content'].strip()

def squash_commits(repo_path, new_message, num_commits):
    """Squash commits and create a new commit with the given message."""
    os.chdir(repo_path)
    
    # Get the actual number of commits in the repository
    result = subprocess.run(['git', 'rev-list', '--count', 'HEAD'], capture_output=True, text=True)
    total_commits = int(result.stdout.strip())
    
    # Use the minimum of num_commits and total_commits
    commits_to_squash = min(num_commits, total_commits)
    
    if commits_to_squash > 1:
        subprocess.run(['git', 'reset', '--soft', f'HEAD~{commits_to_squash - 1}'])
        subprocess.run(['git', 'commit', '--amend', '-m', new_message])
    elif commits_to_squash == 1:
        subprocess.run(['git', 'commit', '--amend', '-m', new_message])
    else:
        print("No commits to squash.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze and squash Git commits using OpenRouter LLM.")
    parser.add_argument("repo_path", help="Path to the Git repository")
    parser.add_argument("--num-commits", type=int, help="Number of recent commits to analyze (default: all commits)")
    args = parser.parse_args()

    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable is not set.")
        exit(1)

    commits = get_commits(args.repo_path, args.num_commits)
    
    print("Commit log messages:")
    for commit in commits:
        print(f"{commit['hash'][:7]}: {commit['message']}")
    print()

    summary = summarize_commits(commits, api_key)
    print("Commit summary:")
    print(summary)
    print()

    confirm = input("Do you want to squash these commits? (y/n): ")
    if confirm.lower() == 'y':
        squash_commits(args.repo_path, summary, len(commits))
        print("Commits have been squashed.")
    else:
        print("Operation cancelled.")
