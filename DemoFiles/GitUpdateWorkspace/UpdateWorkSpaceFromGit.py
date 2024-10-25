# Import necessary libraries
import requests
import json
import msal
import argparse
import os
import time

# Constants

FABRIC_API_URL = "https://api.fabric.microsoft.com/v1"
DEFFAULT_LAKEHOUSE_NAME = "wwilakehouse"
UPD_NOTEBOOK_NAME = "updateWorkspaceDependencies_v1"
CLIENT_ID = ""
TENANT_ID = ""
USERNAME = ""
PASSWORD = ""
WORKSPACE_ID = ""
#  derived variables not input variables
DEFFAULT_LAKEHOUSE_ID = ""
NOTEBOOK_ID = ""
 
# Define a function to acquire token using AAD username password
def acquire_token_user_id_password(tenant_id, client_id,user_name,password):
   print(f"Generating token for Fabric APIs")
   # Initialize the MSAL public client
   authority = f'https://login.microsoftonline.com/{tenant_id}'
   app = msal.PublicClientApplication(client_id, authority=authority)
   scopes = ['https://api.fabric.microsoft.com/.default']   
   result = app.acquire_token_by_username_password(user_name, password, scopes)   
   if 'access_token' in result:
       access_token = result['access_token']
   else:
     access_token = None
   return access_token

def poll_lro_get_status(location_url, headers, delay_second):
    while True:
        #print("inside")
        status_response = requests.get(location_url, headers=headers)
        status_code = status_response.status_code
        #print(status_code)
        if status_code == 200:
            print("Git Sync completed")
            break
        else:
            status = status_response.json().get('Status', 'Unknown')
            if status != "NotStarted" and status != "Running":
                break
            else:
                print("GIT sync operation is still in progress...")
                time.sleep(delay_second)  # Wait for 10 seconds before polling again

def update_workspace_from_GIT(workspace_id, token):
    try:
        print(f"Starting the UpateSync operation for the workspace {workspace_id}")
        headers = {"Authorization": f"Bearer {token}"}
        # Get remoteCommitHash for the git
        gitstatusurl = f"{FABRIC_API_URL}/workspaces/{workspace_id}/git/status"
        response = requests.get(gitstatusurl, headers=headers)

        if response.status_code == 200:
            git_status = response.json()
            remote_commit_hash = git_status['remoteCommitHash']
            workspace_head = git_status['workspaceHead']
            print(f"Remote Commit Hash: {remote_commit_hash}")
            print(f"Workspace Head: {workspace_head}")  

            # Define the update parameters with conflict resolution policy
            update_params ={
                "workspaceHead": workspace_head,
                "remoteCommitHash": remote_commit_hash,
                "conflictResolution": {
                        "conflictResolutionType": "Workspace",
                        "conflictResolutionPolicy": "PreferRemote"
                },    
                "options": {
                    "allowOverrideItems": True
                }
            }
            
            # Update the workspace
            updateworkspaceAllurl = f"{FABRIC_API_URL}/workspaces/{workspace_id}/git/updateFromGit"

            update_response = requests.post(updateworkspaceAllurl, headers=headers, json=update_params)
            
            if update_response.status_code == 200:
                git_status = update_response.json()
                print(f"Workspace {workspace_id} synced successfully with RemoteSync conflict resolution!")
                #print(git_status)
            elif update_response.status_code == 202:
                print('Request accepted, update workspace is in progress.')
                #time.sleep(10)
                location_url = update_response.headers.get("Location")
                #operation = update_response.headers.get("x-ms-operation-id")
                print(f"Polling URL to track operation status is {location_url}")
                #print(f"Polling URL to track operation status is {operation}")
               time.sleep(20)
                poll_lro_get_status(location_url, headers, 10)

            else:
                print(f'Failed to update the workspace. Status Code: {update_response.status_code} - {update_response.text}')
                os._exit(1)
        else:
            print(f'Failed to retrieve Git status. Status Code: {response.status_code}')
            os._exit(1)
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        os._exit(1)  # Stop execution if a request exception occurs

def get_notebook_artifact_id(workspace_id, notebook_name,lakehouse_name,token):

    global DEFFAULT_LAKEHOUSE_ID
    global NOTEBOOK_ID
    
    print(f"Resolving IDs for given Lakehouse {lakehouse_name} and notebook {notebook_name}")
    api_url = f"{FABRIC_API_URL}/workspaces/{workspace_id}/items"
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        items = response.json().get('value', [])
        for item in items:
            
            if item['type'] == 'Notebook' and item['displayName'] == notebook_name:
                NOTEBOOK_ID = item['id']
                print(f"Notebook '{notebook_name}' found with ID: {item['id']}")
            elif item['type'] == 'Lakehouse' and item['displayName'] == lakehouse_name:
                DEFFAULT_LAKEHOUSE_ID = item['id']
                print(f"Default Lakehouse '{lakehouse_name}' found with ID: {item['id']}")                
        return None
    
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        os._exit(1)
    except Exception as err:
        print(f"An error occurred: {err}")
        os._exit(1)

    return None

def invoke_fabric_notebook(workspace_id, notebook_name, lakehouse_name,token):

    try:
        print(f"Starting GIT synchronization for workspace {workspace_id}")

        #Resolving IDs for default lakehouse and notebook.
        get_notebook_artifact_id(workspace_id,notebook_name,lakehouse_name,token)

        payload =   {
        "executionData": {
                    "parameters": {
                        "default_lakehouse": { "value": lakehouse_name,"type": "string" },
                        "workspace_id": { "value": workspace_id,"type": "string" },
                        "notebook_names": { "value": "01 - Create Delta Tables,02 - Data Transformation - Business Aggregates","type": "string" }
                    },            
            "configuration": {
                "defaultLakehouse": {
                    "name": "wwilakehouse",
                    "id": DEFFAULT_LAKEHOUSE_ID,
                    "workspaceId": workspace_id
                },
                "useStarterPool": True
            }
        }
    }
        
        api_url = f"{FABRIC_API_URL}/workspaces/{workspace_id}/items/{NOTEBOOK_ID}/jobs/instances?jobType=RunNotebook"
        #print(api_url) 
        headers = {"Authorization": f"Bearer {token}"}
        #print(payload)
        
        #Run the notebook via API
        print(f"Running notebook {notebook_name} to resolve Item dependencies")
        response = requests.post(api_url, headers=headers, json=payload)
        
        #print(response.content)
        #response.raise_for_status()  # Raise an exception for HTTP errors
        #job_instance = response.json()
        print(f"Notebook {notebook_name} successfully invoked")
        #jobId = job_instance['id']
        #print(f"Job submitted successfully with ID: {jobId}")
        return None
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        os._exit(1)
    except Exception as err:
        print(f"An error occurred: {err}")
        os._exit(1)

    return None

def get_git_status(workspace_id, token):
    try:
        print(f"Retriving latest Workspace commit ID")
        url = f"{FABRIC_API_URL}/workspaces/{workspace_id}/git/status"
        headers = {"Authorization": f"Bearer {token}" }

        response = requests.get(url, headers=headers)
        #response.raise_for_status()
        workspaceheadId = response.json().get("workspaceHead")
        print(f"Latest workspacehead: {workspaceheadId}")
        return workspaceheadId
    except requests.exceptions.RequestException as e:
        print(f"Failed to get Git status: {e}")
        os._exit(1)
        return None

def commit_all_items_to_git(workspace_id,workspace_head, token):
    try:
        print(f"Initialize committ of all changed items for workspace {workspace_id}")
        commit_url = f"{FABRIC_API_URL}/workspaces/{workspace_id}/git/commitToGit"
        headers = {"Authorization": f"Bearer {token}" }
        payload = {
            "mode" : "All",             
            "workspaceHead": workspace_head,
            "commitMessage": "Committing all items from Fabric workspace to Git"
        }
        response = requests.post(commit_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            print("Successfully committed all items to Git.")
        elif response.status_code == 400:
            print("No Changed Items to commmit")
        else:
            print(f"Failed to commit items. Status code: {response.status_code}")
            os._exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Failed to commit items: {e}")
        os._exit(1)


def set_main_parameters():
    parser = argparse.ArgumentParser(description='Update workspace from GIT')
    parser.add_argument('--WORKSPACE_ID', type=str, required=True, help='Workspace ID')
    parser.add_argument('--CLIENT_ID', type=str, required=True, help='Client ID')
    parser.add_argument('--TENANT_ID', type=str, required=True, help='Tenant ID')
    parser.add_argument('--USER_NAME', type=str, required=True, help='Username')
    parser.add_argument('--PASSWORD', type=str, required=True, help='Password')
    parser.add_argument('--DEFFAULT_LAKEHOUSE_NAME', type=str, required=True, help='Lakehouse ID')
    parser.add_argument('--UPD_NOTEBOOK_NAME', type=str, required=True, help='Notebook Name')
    args = parser.parse_args()
    
    global WORKSPACE_ID
    global CLIENT_ID
    global TENANT_ID
    global USERNAME
    global PASSWORD
    global DEFFAULT_LAKEHOUSE_NAME
    global UPD_NOTEBOOK_NAME
    
    WORKSPACE_ID = args.WORKSPACE_ID
    CLIENT_ID = args.CLIENT_ID
    TENANT_ID = args.TENANT_ID
    USERNAME = args.USER_NAME
    PASSWORD = args.PASSWORD
    DEFFAULT_LAKEHOUSE_NAME = args.DEFFAULT_LAKEHOUSE_NAME
    UPD_NOTEBOOK_NAME = args.UPD_NOTEBOOK_NAME

    print(f"Workspace ID {WORKSPACE_ID}" )
    print(f"LakehouseName {DEFFAULT_LAKEHOUSE_NAME}")
    print(f"UserName {USERNAME}")
    
 
def main_func():
   
   set_main_parameters()
   access_token = acquire_token_user_id_password(TENANT_ID, CLIENT_ID,USERNAME,PASSWORD)     
   update_workspace_from_GIT(WORKSPACE_ID,access_token)
   invoke_fabric_notebook(WORKSPACE_ID, UPD_NOTEBOOK_NAME, DEFFAULT_LAKEHOUSE_NAME,access_token)
     
   time.sleep(600)
   workspace_head = get_git_status(WORKSPACE_ID, access_token) 
   commit_all_items_to_git(WORKSPACE_ID,workspace_head,access_token)   
   print("Program Completed")
 
if __name__ == "__main__":
   main_func()

