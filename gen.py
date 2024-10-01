#!.venv/bin/python
import requests
from datetime import datetime, timedelta
import os
import csv
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch GITHUB_TOKEN, USERNAME, and ORGANIZATION_NAME from the .env file
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
USERNAME = os.getenv("USERNAME")  # GitHub username loaded from .env
ORG_NAME = os.getenv("ORG_NAME")  # Organization name loaded from .env
API_URL = "https://api.github.com"

# Get the current month and year
current_year = datetime.now().year
current_month = datetime.now().month
# Adjust to filter repositories updated in the last 30 days
one_month_ago = datetime.now() - timedelta(days=30)

# Generate a CSV filename based on the current month and year
csv_filename = f"commits_{current_year}_{current_month:02d}.csv"


def get_repos(org_name):
    repos = []
    page = 1
    while True:
        url = f"{API_URL}/orgs/{org_name}/repos"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        params = {"page": page, "per_page": 100}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos


def get_branches(repo_name):
    url = f"{API_URL}/repos/{ORG_NAME}/{repo_name}/branches"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_commits(repo, username, branch):
    url = f"{API_URL}/repos/{ORG_NAME}/{repo}/commits"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    params = {
        "author": username,
        "per_page": 100,
        "sha": branch,  # Fetch commits for a specific branch
    }
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 404:
            print(f"Skipping {repo} - Not Found (404)")
        else:
            print(f"HTTP error occurred for {repo}: {http_err}")
        return []
    except Exception as err:
        print(f"An error occurred for {repo}: {err}")
        return []


def is_commit_in_current_month(commit_date_str):
    commit_date = datetime.strptime(commit_date_str, "%Y-%m-%dT%H:%M:%SZ")
    return commit_date.year == current_year and commit_date.month == current_month


def main():
    repos = get_repos(ORG_NAME)
    commits_by_date = {}

    # Open the CSV file for writing
    with open(csv_filename, mode="w", newline="", encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile)
        # Write the header row
        csv_writer.writerow(["date", "repo", "branch", "message", "commit url"])

        for repo in repos:
            # Check if the repo was updated in the last month
            updated_at_str = repo["updated_at"]
            updated_at = datetime.strptime(updated_at_str, "%Y-%m-%dT%H:%M:%SZ")
            if updated_at < one_month_ago:
                print(f"Skipping {repo['name']} - Not updated in the last 30 days")
                continue

            repo_name = repo["name"]

            # Fetch all branches of the repo
            branches = get_branches(repo_name)
            for branch in branches:
                branch_name = branch["name"]
                print(f"Fetching commits for repo: {repo_name}, branch: {branch_name}")
                commits = get_commits(repo_name, USERNAME, branch_name)

                # Process commits
                for commit in commits:
                    commit_date = commit["commit"]["author"]["date"]
                    if is_commit_in_current_month(commit_date):
                        date_str = datetime.strptime(
                            commit_date, "%Y-%m-%dT%H:%M:%SZ"
                        ).date()
                        if date_str not in commits_by_date:
                            commits_by_date[date_str] = []
                        commit_data = {
                            "repo": repo_name,
                            "branch": branch_name,
                            "message": commit["commit"]["message"],
                            "url": commit["html_url"],
                        }
                        commits_by_date[date_str].append(commit_data)

                        # Write each commit to the CSV file
                        csv_writer.writerow(
                            [
                                date_str,
                                repo_name,
                                branch_name,
                                commit_data["message"],
                                commit_data["url"],
                            ]
                        )

    # Print commits grouped by date
    if commits_by_date:
        for date, commits in sorted(commits_by_date.items()):
            print(f"Date: {date}")
            for commit in commits:
                print(
                    f"  Repo: {commit['repo']}, Branch: {commit['branch']}, Message: {commit['message']}, URL: {commit['url']}"
                )
            print("\n")
    else:
        print("No commits found for the current month.")


if __name__ == "__main__":
    main()
