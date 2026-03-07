import { apiClient, API_ENDPOINTS } from "@/config/api";
import type {
  Project,
  CreateProjectInput,
  UpdateProjectInput,
  ListResponse,
} from "@/types";

export const projectService = {
  /**
   * List all projects in a workspace
   */
  async list(
    workspaceId: string,
    skip: number = 0,
    limit: number = 100
  ): Promise<ListResponse<Project>> {
    const response = await apiClient.get<ListResponse<Project>>(
      API_ENDPOINTS.PROJECTS.LIST(workspaceId),
      {
        params: { skip, limit },
      }
    );
    return response.data;
  },

  /**
   * Get a single project
   */
  async get(workspaceId: string, projectId: string): Promise<Project> {
    const response = await apiClient.get<Project>(
      API_ENDPOINTS.PROJECTS.GET(workspaceId, projectId)
    );
    return response.data;
  },

  /**
   * Create a new project
   */
  async create(
    workspaceId: string,
    data: CreateProjectInput
  ): Promise<Project> {
    const response = await apiClient.post<Project>(
      API_ENDPOINTS.PROJECTS.CREATE(workspaceId),
      data
    );
    return response.data;
  },

  /**
   * Update a project
   */
  async update(
    workspaceId: string,
    projectId: string,
    data: UpdateProjectInput
  ): Promise<Project> {
    const response = await apiClient.patch<Project>(
      API_ENDPOINTS.PROJECTS.UPDATE(workspaceId, projectId),
      data
    );
    return response.data;
  },

  /**
   * Delete a project
   */
  async delete(workspaceId: string, projectId: string): Promise<void> {
    await apiClient.delete(
      API_ENDPOINTS.PROJECTS.DELETE(workspaceId, projectId)
    );
  },
};
