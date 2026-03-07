import { apiClient, API_ENDPOINTS } from "@/config/api";
import type {
  Workspace,
  CreateWorkspaceInput,
  UpdateWorkspaceInput,
  ListResponse,
} from "@/types";

export const workspaceService = {
  /**
   * List all workspaces
   */
  async list(skip: number = 0, limit: number = 100): Promise<ListResponse<Workspace>> {
    const response = await apiClient.get<ListResponse<Workspace>>(
      API_ENDPOINTS.WORKSPACES.LIST,
      {
        params: { skip, limit },
      }
    );
    return response.data;
  },

  /**
   * Get a single workspace by ID
   */
  async get(id: string): Promise<Workspace> {
    const response = await apiClient.get<Workspace>(
      API_ENDPOINTS.WORKSPACES.GET(id)
    );
    return response.data;
  },

  /**
   * Create a new workspace
   */
  async create(data: CreateWorkspaceInput): Promise<Workspace> {
    const response = await apiClient.post<Workspace>(
      API_ENDPOINTS.WORKSPACES.CREATE,
      data
    );
    return response.data;
  },

  /**
   * Update a workspace
   */
  async update(id: string, data: UpdateWorkspaceInput): Promise<Workspace> {
    const response = await apiClient.patch<Workspace>(
      API_ENDPOINTS.WORKSPACES.UPDATE(id),
      data
    );
    return response.data;
  },

  /**
   * Delete a workspace
   */
  async delete(id: string): Promise<void> {
    await apiClient.delete(API_ENDPOINTS.WORKSPACES.DELETE(id));
  },
};
