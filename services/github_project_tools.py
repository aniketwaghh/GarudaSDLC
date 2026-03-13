"""
GitHub Project Management Tools - GraphQL Operations
Tools for GitHub Projects V2 operations that cannot be done via REST API/MCP.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field
import os
import httpx


class GitHubGraphQLClient:
    """Client for GitHub GraphQL API"""
    
    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.api_url = "https://api.github.com/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def execute(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute GraphQL query"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                json={"query": query, "variables": variables or {}},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()


# ============================================================================
# PROJECT QUERIES
# ============================================================================

class GetUserProjectsInput(BaseModel):
    """Get all projects for a user"""
    username: str = Field(..., description="GitHub username")
    first: int = Field(20, description="Number of projects to fetch", ge=1, le=100)


class GetOrgProjectsInput(BaseModel):
    """Get all projects for an organization"""
    org_name: str = Field(..., description="GitHub organization name")
    first: int = Field(20, description="Number of projects to fetch", ge=1, le=100)


class GetProjectByNumberInput(BaseModel):
    """Get project by its number"""
    owner: str = Field(..., description="Username or organization name")
    owner_type: Literal["user", "organization"] = Field(..., description="Type of owner")
    project_number: int = Field(..., description="Project number from URL")


class GetProjectFieldsInput(BaseModel):
    """Get all fields configuration for a project"""
    project_id: str = Field(..., description="Project node ID (e.g., PVT_kwHOBKy1Ec4BRSq3)")


class ListProjectItemsInput(BaseModel):
    """List all items in a project with their status"""
    project_id: str = Field(..., description="Project node ID")
    first: int = Field(50, description="Number of items to fetch", ge=1, le=100)
    include_closed: bool = Field(True, description="Include closed/done items")


class ListProjectItemsByStatusInput(BaseModel):
    """List items filtered by status/bucket"""
    project_id: str = Field(..., description="Project node ID")
    status: str = Field(..., description="Status name (e.g., 'Backlog', 'In Progress', 'Done')")
    first: int = Field(50, description="Number of items to fetch")


# ============================================================================
# PROJECT MUTATIONS
# ============================================================================

class AddIssueToProjectInput(BaseModel):
    """Add an issue or PR to a project board"""
    project_id: str = Field(..., description="Project node ID (PVT_...)")
    content_id: str = Field(..., description="Issue/PR node ID (I_... or PR_...)")


class UpdateProjectItemStatusInput(BaseModel):
    """Move an item to a different status/bucket"""
    project_id: str = Field(..., description="Project node ID")
    item_id: str = Field(..., description="Project item ID (PVTI_...)")
    status_field_id: str = Field(..., description="Status field ID (PVTSSF_...)")
    status_option_id: str = Field(..., description="Status option ID (e.g., 'f75ad846' for Backlog)")


class UpdateProjectItemFieldInput(BaseModel):
    """Update a custom field value for a project item"""
    project_id: str = Field(..., description="Project node ID")
    item_id: str = Field(..., description="Project item ID")
    field_id: str = Field(..., description="Field ID to update")
    field_type: Literal["text", "number", "date", "singleSelect", "iteration"] = Field(
        ..., description="Type of field being updated"
    )
    value: Any = Field(..., description="Value to set (type depends on field_type)")


class RemoveItemFromProjectInput(BaseModel):
    """Remove an item from a project"""
    project_id: str = Field(..., description="Project node ID")
    item_id: str = Field(..., description="Project item ID to remove")


class CreateProjectInput(BaseModel):
    """Create a new project"""
    owner_id: str = Field(..., description="Owner node ID (user or org)")
    title: str = Field(..., description="Project title")
    description: Optional[str] = Field(None, description="Project description")


# ============================================================================
# ISSUE LINKING (SUB-ISSUES)
# ============================================================================

class LinkSubIssueInput(BaseModel):
    """Link a sub-issue to parent issue (using tasklist references)"""
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    parent_issue_number: int = Field(..., description="Parent issue number")
    sub_issue_number: int = Field(..., description="Sub-issue number to link")


class GetIssueWithSubIssuesInput(BaseModel):
    """Get issue with all its sub-issues"""
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    issue_number: int = Field(..., description="Issue number")


class GetIssueNodeIdInput(BaseModel):
    """Get node ID for an issue by number"""
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    issue_number: int = Field(..., description="Issue number")


# ============================================================================
# ADVANCED QUERIES
# ============================================================================

class ListIssuesByProjectStatusInput(BaseModel):
    """List all issues with their project status"""
    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    project_id: str = Field(..., description="Project node ID")
    status_filter: Optional[str] = Field(None, description="Filter by status name")


class GetProjectStatusOptionsInput(BaseModel):
    """Get all available status options for a project"""
    project_id: str = Field(..., description="Project node ID")


class BulkMoveItemsInput(BaseModel):
    """Move multiple items to a new status"""
    project_id: str = Field(..., description="Project node ID")
    item_ids: List[str] = Field(..., description="List of project item IDs")
    status_field_id: str = Field(..., description="Status field ID")
    status_option_id: str = Field(..., description="Target status option ID")


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

class GitHubProjectTools:
    """GitHub Project Management Tools using GraphQL"""
    
    def __init__(self, token: Optional[str] = None):
        self.client = GitHubGraphQLClient(token)
    
    async def get_user_projects(self, input: GetUserProjectsInput) -> Dict[str, Any]:
        """Get all projects for a user"""
        query = """
        query($username: String!, $first: Int!) {
          user(login: $username) {
            projectsV2(first: $first) {
              nodes {
                id
                number
                title
                url
                shortDescription
                closed
                createdAt
                updatedAt
              }
            }
          }
        }
        """
        return await self.client.execute(query, {
            "username": input.username,
            "first": input.first
        })
    
    async def get_project_by_number(self, input: GetProjectByNumberInput) -> Dict[str, Any]:
        """Get specific project by number"""
        owner_field = "user" if input.owner_type == "user" else "organization"
        query = f"""
        query($owner: String!, $number: Int!) {{
          {owner_field}(login: $owner) {{
            projectV2(number: $number) {{
              id
              number
              title
              url
              shortDescription
              closed
              readme
              createdAt
              updatedAt
            }}
          }}
        }}
        """
        return await self.client.execute(query, {
            "owner": input.owner,
            "number": input.project_number
        })
    
    async def get_project_fields(self, input: GetProjectFieldsInput) -> Dict[str, Any]:
        """Get all fields and their options for a project"""
        query = """
        query($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              fields(first: 20) {
                nodes {
                  ... on ProjectV2Field {
                    id
                    name
                  }
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                    options {
                      id
                      name
                    }
                  }
                  ... on ProjectV2IterationField {
                    id
                    name
                    configuration {
                      iterations {
                        id
                        title
                        startDate
                      }
                    }
                  }
                }
              }
            }
          }
        }
        """
        return await self.client.execute(query, {"projectId": input.project_id})
    
    async def list_project_items(self, input: ListProjectItemsInput) -> Dict[str, Any]:
        """List all items in a project with their status"""
        query = """
        query($projectId: ID!, $first: Int!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              title
              items(first: $first) {
                totalCount
                nodes {
                  id
                  fieldValues(first: 8) {
                    nodes {
                      ... on ProjectV2ItemFieldSingleSelectValue {
                        name
                        field {
                          ... on ProjectV2FieldCommon {
                            name
                          }
                        }
                      }
                      ... on ProjectV2ItemFieldTextValue {
                        text
                        field {
                          ... on ProjectV2FieldCommon {
                            name
                          }
                        }
                      }
                    }
                  }
                  content {
                    ... on Issue {
                      number
                      title
                      url
                      state
                      assignees(first: 5) {
                        nodes {
                          login
                        }
                      }
                      labels(first: 10) {
                        nodes {
                          name
                        }
                      }
                    }
                    ... on PullRequest {
                      number
                      title
                      url
                      state
                    }
                    ... on DraftIssue {
                      title
                      body
                    }
                  }
                }
              }
            }
          }
        }
        """
        return await self.client.execute(query, {
            "projectId": input.project_id,
            "first": input.first
        })
    
    async def add_issue_to_project(self, input: AddIssueToProjectInput) -> Dict[str, Any]:
        """Add an issue or PR to a project board"""
        mutation = """
        mutation($projectId: ID!, $contentId: ID!) {
          addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
            item {
              id
            }
          }
        }
        """
        return await self.client.execute(mutation, {
            "projectId": input.project_id,
            "contentId": input.content_id
        })
    
    async def update_item_status(self, input: UpdateProjectItemStatusInput) -> Dict[str, Any]:
        """Move an item to a different status/bucket"""
        mutation = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
          updateProjectV2ItemFieldValue(
            input: {
              projectId: $projectId
              itemId: $itemId
              fieldId: $fieldId
              value: { singleSelectOptionId: $optionId }
            }
          ) {
            projectV2Item {
              id
            }
          }
        }
        """
        return await self.client.execute(mutation, {
            "projectId": input.project_id,
            "itemId": input.item_id,
            "fieldId": input.status_field_id,
            "optionId": input.status_option_id
        })
    
    async def remove_item_from_project(self, input: RemoveItemFromProjectInput) -> Dict[str, Any]:
        """Remove an item from a project"""
        mutation = """
        mutation($projectId: ID!, $itemId: ID!) {
          deleteProjectV2Item(input: {projectId: $projectId, itemId: $itemId}) {
            deletedItemId
          }
        }
        """
        return await self.client.execute(mutation, {
            "projectId": input.project_id,
            "itemId": input.item_id
        })
    
    async def create_project(self, input: CreateProjectInput) -> Dict[str, Any]:
        """Create a new project"""
        mutation = """
        mutation($ownerId: ID!, $title: String!) {
          createProjectV2(input: {ownerId: $ownerId, title: $title}) {
            projectV2 {
              id
              number
              title
              url
            }
          }
        }
        """
        return await self.client.execute(mutation, {
            "ownerId": input.owner_id,
            "title": input.title
        })
    
    async def get_issue_node_id(self, input: GetIssueNodeIdInput) -> Dict[str, Any]:
        """Get node ID for an issue"""
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            issue(number: $number) {
              id
              number
              title
            }
          }
        }
        """
        return await self.client.execute(query, {
            "owner": input.owner,
            "repo": input.repo,
            "number": input.issue_number
        })
    
    async def get_issue_with_subissues(self, input: GetIssueWithSubIssuesInput) -> Dict[str, Any]:
        """Get issue with all its sub-issues"""
        query = """
        query($owner: String!, $repo: String!, $number: Int!) {
          repository(owner: $owner, name: $repo) {
            issue(number: $number) {
              id
              number
              title
              body
              state
              url
              trackedIssues(first: 50) {
                totalCount
                nodes {
                  number
                  title
                  state
                  url
                }
              }
            }
          }
        }
        """
        return await self.client.execute(query, {
            "owner": input.owner,
            "repo": input.repo,
            "number": input.issue_number
        })
    
    async def get_project_status_options(self, input: GetProjectStatusOptionsInput) -> Dict[str, Any]:
        """Get all status options for a project"""
        query = """
        query($projectId: ID!) {
          node(id: $projectId) {
            ... on ProjectV2 {
              fields(first: 20) {
                nodes {
                  ... on ProjectV2SingleSelectField {
                    id
                    name
                    options {
                      id
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """
        return await self.client.execute(query, {"projectId": input.project_id})
    
    async def bulk_move_items(self, input: BulkMoveItemsInput) -> Dict[str, Any]:
        """Move multiple items to a new status"""
        # Build mutation with multiple updates
        mutations = []
        for idx, item_id in enumerate(input.item_ids):
            mutations.append(f"""
            item{idx}: updateProjectV2ItemFieldValue(
              input: {{
                projectId: "{input.project_id}"
                itemId: "{item_id}"
                fieldId: "{input.status_field_id}"
                value: {{ singleSelectOptionId: "{input.status_option_id}" }}
              }}
            ) {{
              projectV2Item {{
                id
              }}
            }}
            """)
        
        mutation = f"""
        mutation {{
          {' '.join(mutations)}
        }}
        """
        return await self.client.execute(mutation)


# ============================================================================
# TOOL DEFINITIONS FOR AGENT FRAMEWORKS
# ============================================================================

GITHUB_PROJECT_TOOLS_SCHEMAS = {
    "get_user_projects": {
        "name": "get_user_projects",
        "description": "Get all GitHub Projects for a user",
        "input_schema": GetUserProjectsInput.model_json_schema()
    },
    "get_org_projects": {
        "name": "get_org_projects",
        "description": "Get all GitHub Projects for an organization",
        "input_schema": GetOrgProjectsInput.model_json_schema()
    },
    "get_project_by_number": {
        "name": "get_project_by_number",
        "description": "Get a specific project by its number",
        "input_schema": GetProjectByNumberInput.model_json_schema()
    },
    "get_project_fields": {
        "name": "get_project_fields",
        "description": "Get all fields and options for a project (Status, Priority, etc.)",
        "input_schema": GetProjectFieldsInput.model_json_schema()
    },
    "list_project_items": {
        "name": "list_project_items",
        "description": "List all items in a project with their status and details",
        "input_schema": ListProjectItemsInput.model_json_schema()
    },
    "add_issue_to_project": {
        "name": "add_issue_to_project",
        "description": "Add an issue or pull request to a project board",
        "input_schema": AddIssueToProjectInput.model_json_schema()
    },
    "update_item_status": {
        "name": "update_item_status",
        "description": "Move a project item to a different status/bucket (e.g., Backlog to In Progress)",
        "input_schema": UpdateProjectItemStatusInput.model_json_schema()
    },
    "remove_item_from_project": {
        "name": "remove_item_from_project",
        "description": "Remove an item from a project board",
        "input_schema": RemoveItemFromProjectInput.model_json_schema()
    },
    "create_project": {
        "name": "create_project",
        "description": "Create a new GitHub Project",
        "input_schema": CreateProjectInput.model_json_schema()
    },
    "get_issue_node_id": {
        "name": "get_issue_node_id",
        "description": "Get the node ID for an issue (required for project operations)",
        "input_schema": GetIssueNodeIdInput.model_json_schema()
    },
    "get_issue_with_subissues": {
        "name": "get_issue_with_subissues",
        "description": "Get an issue with all its linked sub-issues",
        "input_schema": GetIssueWithSubIssuesInput.model_json_schema()
    },
    "get_project_status_options": {
        "name": "get_project_status_options",
        "description": "Get all available status options for a project",
        "input_schema": GetProjectStatusOptionsInput.model_json_schema()
    },
    "bulk_move_items": {
        "name": "bulk_move_items",
        "description": "Move multiple items to a new status at once",
        "input_schema": BulkMoveItemsInput.model_json_schema()
    },
}


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        tools = GitHubProjectTools()
        
        # Example: Get user projects
        result = await tools.get_user_projects(
            GetUserProjectsInput(username="aniketwaghh")
        )
        print(result)
    
    asyncio.run(main())
