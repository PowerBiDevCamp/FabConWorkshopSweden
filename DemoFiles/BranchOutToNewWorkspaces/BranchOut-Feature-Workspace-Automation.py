import requests
import json
import msal
import argparse
import os

# Constants

FABRIC_API_URL = "https://api.fabric.microsoft.com/v1"
ADO_API_URL = ""
CAPACITY_ID = ""
WORKSPACE_NAME = ""
DEVELOPER_ID = ""
ADO_MAIN_BRANCH = ""
ADO_NEW_BRANCH = ""
ADO_PROJECT_NAME = ""
ADO_REPO_NAME = ""
ADO_ORG_NAME = ""
CLIENT_ID = ""
CLIENT_SECRET = ""
TENANT_ID = ""
USERNAME = ""
PASSWORD = ""



# Define a function to acquire token for ADO using using AAD username password
def acquire_ado_token_user_id_password(tenant_id, client_id,user_name,password):
   
   print("Generating ADO token in progress...")
   # Initialize the MSAL public client
   authority = f'https://login.microsoftonline.com/{tenant_id}'
   app = msal.PublicClientApplication(client_id, authority=authority)
   scopes = ['499b84ac-1321-427f-aa17-267ca6975798/.default']
   result = app.acquire_token_by_username_password(user_name, password, scopes)
   if 'access_token' in result:
       access_token = result['access_token']
       print(" ADO token Generated")
   else:
     access_token = None
   return access_token

# Define a function to acquire token using AAD username password
def acquire_token_user_id_password(tenant_id, client_id,user_name,password):
   
   # Initialize the MSAL public client
   print("Generating Token for Microsoft Fabric in progress...")
   authority = f'https://login.microsoftonline.com/{tenant_id}'
   app = msal.PublicClientApplication(client_id, authority=authority)
   scopes = ['https://api.fabric.microsoft.com/.default']   
   result = app.acquire_token_by_username_password(user_name, password, scopes)   
   if 'access_token' in result:
       access_token = result['access_token']
       print("Generating Token for Microsoft Fabric generated")

   else:
     access_token = None
   return access_token

# Define a function to acquire token using SPN
def acquire_token_spn(tenant_id,client_id,client_secret):
    app = msal.ConfidentialClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        client_credential=client_secret
    )
    result = app.acquire_token_for_client(scopes=SCOPES)
    if "access_token" in result:
        return result["access_token"]
    else:
        print(f"Error acquiring token: {result.get('error_description')}")
        return None


# Function to create a Fabric workspace
def create_fabric_workspace(workspace_name,token):
    try:
        print(f"Creating Fabric Workspace {WORKSPACE_NAME} in progress...  ")
        headers = {"Authorization": f"Bearer {token}"}
        data = {
             "displayName": workspace_name,
            "capacityId": CAPACITY_ID
        }
        #response = requests.post(f"{FABRIC_API_URL}/workspaces", headers=headers, json={"displayName": workspace_name})
        response = requests.post(f"{FABRIC_API_URL}/workspaces", headers=headers, json=data)

        print(f"Fabric Workspace {WORKSPACE_NAME} created with ID: {response.json()['id']} successfully... ")
        return response.json()["id"]
    except requests.exceptions.RequestException as e:
        if e.status_code == 409:  # Conflict error, workspace already exists
            print(f"Workspace '{workspace_name}' already exists.")
            return None
        print(f"Error creating workspace: {e}")
        os._exit(1)
        return None

# Function to assign workspace to a capacity
def assign_workspace_to_capacity(workspace_id, capacity_id, token):
    try:
        print(f"Assing Fabric Workspace {WORKSPACE_NAME}  to {capacity_id} is in progress...  ")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(f"{FABRIC_API_URL}/workspaces/{workspace_id}/assignToCapacity", headers=headers, json={"capacityId": capacity_id})
        response.raise_for_status()
        print("Capacity Assigned.")
    except requests.exceptions.RequestException as e:
        print(f"Error assigning workspace to capacity: {e}")
        os._exit(1)

# Function to add developers as workspace admins
"""
def add_workspace_admins(workspace_id, developers, token):
    try:
        print(f"Adding developer to workspace {WORKSPACE_NAME} in progress")
        headers = {"Authorization": f"Bearer {token}"}
        for developerId in DEVELOPER_ID:
            data = {
                    "principal" : {
                        "id": developerId,
                        "type": "User"
                    },
                    "role": "Admin"
                }
            response = requests.post(f"{FABRIC_API_URL}/workspaces/{workspace_id}/roleAssignments", headers=headers, json=data)
            response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error adding workspace admin: {e}")
        os._exit(1)
"""
def add_workspace_admins(workspace_id, developerId, token):
    try:
        print(f"Adding developer to workspace {WORKSPACE_NAME} in progress")
        headers = {"Authorization": f"Bearer {token}"}
       # for developerId in DEVELOPER_ID:
        data = {
                "principal" : {
                    "id": developerId,
                    "type": "User"
                },
                "role": "Admin"
            }
        response = requests.post(f"{FABRIC_API_URL}/workspaces/{workspace_id}/roleAssignments", headers=headers, json=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error adding workspace admin: {e}")
        os._exit(1)        

# Function to create a new branch in Azure DevOps
def create_azure_devops_branch(project_name, repo_name, main_branch, new_branch):
    try:
        token = acquire_ado_token_user_id_password(TENANT_ID, CLIENT_ID,USERNAME,PASSWORD)
        #print("ADO token generat")
        print(f"Creating feature branch {new_branch} based on {main_branch} in progress")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        data =  [
                 {
                "name":f"refs/heads/{new_branch}",
                "oldObjectId": "0000000000000000000000000000000000000000",
                "newObjectId": get_branch_object_id(project_name, repo_name, main_branch, token)
                }
            ]
        response = requests.post(f"{ADO_API_URL}/{project_name}/_apis/git/repositories/{repo_name}/refs?api-version=7.1", headers=headers, json=data)
        response.raise_for_status()
        print(f"Feature branch {new_branch} created")
    except requests.exceptions.RequestException as e:
        print(f"Error creating Azure DevOps branch: {e}")
        os._exit(1)

# Helper function to get the object ID of a branch
def get_branch_object_id(project_name, repo_name, branch_name, token):
    try:
        print(f"Retriving ID of main branch {branch_name} to be cloned ")
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{ADO_API_URL}/{project_name}/_apis/git/repositories/{repo_name}/refs/heads/{branch_name}?api-version=7.1", headers=headers)
        response.raise_for_status()
        #print(f"BranchID: {response.json()["value"][0]["objectId"]}")        
        return response.json()["value"][0]["objectId"]
    except requests.exceptions.RequestException as e:
        print(f"Error getting branch object ID: {e}")
        return None

# Function to connect Azure DevOps branch to Fabric workspace
def connect_branch_to_workspace(workspace_id, project_name, org_name, repo_name, branch_name, token):
    try:
        print(f"Conecting workspace {workspace_id} to feature branch {branch_name} is in progess..")
        headers = {"Authorization": f"Bearer {token}"}
        data = {
        "gitProviderDetails": {
                "organizationName": org_name,
                "projectName": project_name,
                "gitProviderType": "AzureDevOps",
                "repositoryName": repo_name,
                "branchName": branch_name,
                "directoryName": ""
         }
        } 
       # print(data)
        response = requests.post(f"{FABRIC_API_URL}/workspaces/{workspace_id}/git/connect", headers=headers, json=data)
        #print(response)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error connecting branch to workspace: {e}")

def initialize_workspace_from_git(workspace_id,token):

    try:
        print(f"Connecting f{WORKSPACE_NAME} to feature branch {ADO_NEW_BRANCH} is in propress... ")
        headers = {"Authorization": f"Bearer {token}"}
        # Initialize the connection to the GIT repository
        gitinitializeurl = f"{FABRIC_API_URL}/workspaces/{workspace_id}/git/initializeConnection"
        response = requests.post(gitinitializeurl, headers=headers)
        
        print(response.json())
        
        if response.status_code == 200:
            git_status = response.json()
            remote_commit_hash = git_status['remoteCommitHash']
            workspace_head = git_status['workspaceHead']
            
            # Define the update parameters with conflict resolution policy
            update_params = {
                'workspaceHead': workspace_head,
                'remoteCommitHash': remote_commit_hash,
                'options': {
                    'allowOverrideItems': True,
                    'conflictResolution': 'RemoteSync'  # Set conflict resolution to RemoteSync
                }
            }
            
            # Update the workspace
            updateworkspaceAllurl = f"{FABRIC_API_URL}/workspaces/{workspace_id}/git/updateFromGit"
            update_response = requests.post(updateworkspaceAllurl, headers=headers, json=update_params)
            
            if update_response.status_code == 200:
                git_status = update_response.json()
                print(f"Feature workspace {WORKSPACE_NAME} is synchronizing with feature branch {ADO_NEW_BRANCH} ")
                #print(git_status)
            elif update_response.status_code == 202:
                print('Request accepted, update workspace is in progress.')
            else:
                print(f'Failed to update the workspace. Status Code: {update_response.status_code} - {update_response.text}')
        
        elif response.status_code == 202:
            print('Request accepted, get initialize in progress. Retry after some time')
        
        else:
            print(f'Failed to Git initialize. Status Code: {response.status_code}')
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        os._exit(1)

# Main function to execute the tasks

def set_main_parameters():
    global TENANT_ID
    global CLIENT_ID
    global USERNAME
    global PASSWORD
    global WORKSPACE_NAME
    global DEVELOPER_ID
    global ADO_MAIN_BRANCH
    global ADO_NEW_BRANCH
    global ADO_PROJECT_NAME
    global ADO_REPO_NAME
    global ADO_ORG_NAME
    global ADO_API_URL
    global CLIENT_SECRET
    global CAPACITY_ID

    parser = argparse.ArgumentParser()
    parser.add_argument('--TENANT_ID',type=str, help= 'TenantID passed from Devops')
    parser.add_argument('--CLIENT_ID',type=str, help= 'ClientID passed from Devops')
    parser.add_argument('--CLIENT_SECRET',type=str, help= 'CLIENTSECRET passed from Devops')
    parser.add_argument('--USER_NAME',type=str, help= 'User Name passed from Devops')
    parser.add_argument('--PASSWORD',type=str, help= 'User password passed from Devops')
    parser.add_argument('--WORKSPACE_NAME',type=str, help= 'Name of the feature workspace to be created')
    parser.add_argument('--DEVELOPER_ID',type=str, help= 'Developr IDs to be added to workspace as admin')
    parser.add_argument('--ADO_MAIN_BRANCH',type=str, help= 'Main development branch')
    parser.add_argument('--ADO_NEW_BRANCH',type=str, help= 'New branch to be created')
    parser.add_argument('--ADO_PROJECT_NAME',type=str, help= 'ADO project name')
    parser.add_argument('--ADO_REPO_NAME',type=str, help= 'ADO repository name')
    parser.add_argument('--ADO_ORG_NAME',type=str, help= 'ADO organization name')
    parser.add_argument('--ADO_API_URL',type=str, help= 'ADO organization name')
    parser.add_argument('--CAPACITY_ID',type=str, help= 'Capacity ID to assign the workspace')    
    args = parser.parse_args()

    # Define your tenant_id, client_id, client_secret, workspace_name, developer_username, project_name, repository_name, and branch_name
    TENANT_ID = args.TENANT_ID
    CLIENT_ID = args.CLIENT_ID
    USERNAME = args.USER_NAME
    PASSWORD = args.PASSWORD
    WORKSPACE_NAME = args.WORKSPACE_NAME    
    DEVELOPER_ID = args.DEVELOPER_ID
    ADO_MAIN_BRANCH = args.ADO_MAIN_BRANCH
    ADO_NEW_BRANCH = args.ADO_NEW_BRANCH
    ADO_PROJECT_NAME = args.ADO_PROJECT_NAME
    ADO_REPO_NAME = args.ADO_REPO_NAME
    ADO_ORG_NAME = args.ADO_ORG_NAME
    ADO_API_URL = args.ADO_API_URL
    CLIENT_SECRET = args.CLIENT_SECRET
    CAPACITY_ID = args.CAPACITY_ID

    print(TENANT_ID)
    print(ADO_ORG_NAME)   
    print(DEVELOPER_ID)
    print(PASSWORD)


def main():

    set_main_parameters()
    token = ""
    token = acquire_token_user_id_password(TENANT_ID, CLIENT_ID,USERNAME,PASSWORD)
    if token:
        #print( "AAD Token Generated Successfully")    
        workspace_id = create_fabric_workspace(WORKSPACE_NAME, token)
       # print(f"Workspace {WORKSPACE_NAME} Created Successfully {workspace_id} and assigned to capacity {CAPACITY_ID}")
        #workspace_id = "f4eaaf87-bab4-429a-99f8-a1034236cf54"
        if workspace_id:
           #part of WS creation
           #assign_workspace_to_capacity(workspace_id, CAPACITY_ID, token)           
           add_workspace_admins(workspace_id, DEVELOPER_ID, token)
           create_azure_devops_branch(ADO_PROJECT_NAME, ADO_REPO_NAME, ADO_MAIN_BRANCH, ADO_NEW_BRANCH)           
           connect_branch_to_workspace(workspace_id, ADO_PROJECT_NAME, ADO_ORG_NAME,ADO_REPO_NAME, ADO_NEW_BRANCH, token)
           initialize_workspace_from_git(workspace_id, token)
           

if __name__ == "__main__":
    main()
    
