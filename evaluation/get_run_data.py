import os
import requests
import json
import zipfile
import shutil
from datetime import datetime, timedelta
from dotenv import load_dotenv

token = None
repo = None
headers = None

api_url = "https://api.github.com/repos/"

def get_workflow_runs(workflow_name, run_limit=30):
    """Get runs for a specific workflow by name or ID"""
    # with id
    workflow_id = workflow_name
    if not str(workflow_name).isdigit():
        workflow_url = f"{api_url}{repo}/actions/workflows/{workflow_name}"
        response = requests.get(workflow_url, headers=headers)
        response.raise_for_status()
        workflow_id = response.json().get("id")
    
    # get by id
    url = f"{api_url}{repo}/actions/workflows/{workflow_id}/runs"
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    runs = response.json().get("workflow_runs", [])
    return runs[:run_limit]  # limit

def filter_non_skipped_runs(runs):
    """filter out workflow runs that are skipped because of no issues to process"""
    filtered_runs = []
    
    for run in runs:
        run_id = run["id"]
        jobs_url = f"{api_url}{repo}/actions/runs/{run_id}/jobs"
        response = requests.get(jobs_url, headers=headers)
        
        if response.status_code == 200:
            jobs = response.json().get("jobs", [])
            # Check if any jobs besides the "skipped" job actually ran
            non_skipped_jobs = [job for job in jobs if job["name"] != "skipped" and job["conclusion"] is not None]
            if non_skipped_jobs:
                filtered_runs.append(run)
    
    return filtered_runs

def get_run_usage_metrics(run_id):
    """Get usage metrics for a specific workflow run"""
    url = f"{api_url}{repo}/actions/runs/{run_id}/timing"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json()

def get_run_artifacts(run_id):
    """Get artifacts for a specific workflow run"""
    url = f"{api_url}{repo}/actions/runs/{run_id}/artifacts"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    return response.json().get("artifacts", [])

def get_run_jobs(run_id):
    """Get detailed job information for a specific workflow run"""
    url = f"{api_url}{repo}/actions/runs/{run_id}/jobs"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    
    jobs = response.json().get("jobs", [])
    
    job_details = []
    for job in jobs:
        # Parse start and completion times
        started_at = datetime.fromisoformat(job["started_at"].replace("Z", "+00:00")) if job.get("started_at") else None
        completed_at = datetime.fromisoformat(job["completed_at"].replace("Z", "+00:00")) if job.get("completed_at") else None
        
        # Calculate duration if both timestamps exist
        duration = None
        if started_at and completed_at:
            duration = (completed_at - started_at).total_seconds()
        
        job_details.append({
            "job_id": job["id"],
            "name": job["name"],
            "status": job["status"],
            "conclusion": job["conclusion"],
            "started_at": job["started_at"],
            "completed_at": job["completed_at"],
            "duration_seconds": duration,
        })
    
    return job_details

def download_artifact(artifact, destination_folder):
    """Download an artifact to the specified folder and extract relevant files"""
    url = artifact["archive_download_url"]
    
    # Create a session that will follow redirects
    session = requests.Session()
    response = session.get(url, headers=headers, stream=True)
    response.raise_for_status()
    
    # Get the artifact filename from headers if available, or use the artifact name
    filename = artifact["name"] + ".zip"
    if "content-disposition" in response.headers:
        content_disposition = response.headers.get("content-disposition")
        if "filename=" in content_disposition:
            filename = content_disposition.split("filename=")[1].strip('"')
    
    artifact_path = os.path.join(destination_folder, filename)
    
    # Download the zip file
    with open(artifact_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    
    # Extract the zip file
    temp_extract_path = os.path.join(destination_folder, "temp_extract")
    os.makedirs(temp_extract_path, exist_ok=True)
    
    try:
        with zipfile.ZipFile(artifact_path, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_path)
        
        # Find files that are two folders deep and move them to the destination folder
        extracted_files = []
        for root, dirs, files in os.walk(temp_extract_path):
            # Calculate depth relative to temp_extract_path
            rel_path = os.path.relpath(root, temp_extract_path)
            path_parts = rel_path.split(os.sep)
            
            # If we're two folders deep
            if len(path_parts) == 2 and path_parts[0] != '.':
                for file in files:
                    source_file = os.path.join(root, file)
                    dest_file = os.path.join(destination_folder, file)
                    shutil.copy2(source_file, dest_file)
                    extracted_files.append(dest_file)
                    print(f"  - Extracted: {file}")
        
        # Clean up temporary files
        shutil.rmtree(temp_extract_path)
        os.remove(artifact_path)  # Remove the zip file
        
        return extracted_files
    
    except Exception as e:
        print(f"Error extracting artifact: {e}")
        # If extraction fails, still return the zip path
        return [artifact_path]


def get_run_data(workflow_name, run_limit=1):
    """get runs, metrics, and artifacts of a workflow"""
    all_runs = get_workflow_runs(workflow_name, run_limit)
    print(f"Found {len(all_runs)} total runs")

    filtered_runs = filter_non_skipped_runs(all_runs)
    print(f"Found {len(filtered_runs)} non-skipped runs")

    for run in filtered_runs:
        run_id = run["id"]
        run_folder = f"run_{run_id}"
        os.makedirs(run_folder, exist_ok=True)
        print(f"Created folder for run {run_id}: {run_folder}")

        run_id = run_id
        run_data = {
            "run_id": run_id,
            "status": run["status"],
            "conclusion": run["conclusion"],
            "created_at": run["created_at"],
            "updated_at": run["updated_at"],
            "html_url": run["html_url"]
        }
        
        # fetch detailed job information
        try:
            jobs = get_run_jobs(run_id)
            run_data["jobs"] = jobs

            total_duration = calculate_total_duration(jobs)
            run_data["total_duration_seconds"] = total_duration
        except Exception as e:
            print(f"Error getting job details for run {run_id}: {e}")
            run_data["jobs"] = None
        
        # fetch usage metrics
        try:
            metrics = get_run_usage_metrics(run_id)
            run_data["metrics"] = metrics
        except Exception as e:
            print(f"Error getting metrics for run {run_id}: {e}")
            run_data["metrics"] = None
        
        # fetch artifacts
        try:
            artifacts = get_run_artifacts(run_id)
            run_data["artifacts"] = artifacts

            for artifact in artifacts:
                try:
                    download_artifact(artifact, run_folder)
                    print(f"Downloaded and extracted artifact: {artifact['name']}")
                except Exception as e:
                    print(f"Error downloading artifact {artifact['name']}: {e}")
            
        except Exception as e:
            print(f"Error getting artifacts for run {run_id}: {e}")
            run_data["artifacts"] = None

        ci_run_data_file = os.path.join(run_folder, "ci_run_data.json")
        with open(ci_run_data_file, "w") as f:
            json.dump(run_data, f, indent=2)
        print(f"Saved run data to {ci_run_data_file}")


def calculate_total_duration(jobs):
    if not jobs:
        return 0
    start_times = [datetime.fromisoformat(job["started_at"].replace("Z", "+00:00")) for job in jobs]
    end_times = [datetime.fromisoformat(job["completed_at"].replace("Z", "+00:00")) for job in jobs]

    earliest_start = min(start_times)
    latest_end = max(end_times)

    total_duration = (latest_end - earliest_start).total_seconds()
    return total_duration


def main():
    global token, repo, headers

    load_dotenv()

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPO")


    if not token or not repo:
        print("Error: GITHUB_TOKEN and GITHUB_REPO environment variables must be set")
        print(f"Current repo value: {repo}")
        return
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"
    }

    workflow_name = "auto-fix.yml"
    
    print(f"fetching workflow runs for {workflow_name} in repository {repo}")

    get_run_data(workflow_name)


if __name__ == "__main__":
    main()
