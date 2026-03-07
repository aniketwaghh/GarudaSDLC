// Workspace Types
export interface Workspace {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateWorkspaceInput {
  name: string;
  description?: string;
}

export interface UpdateWorkspaceInput {
  name?: string;
  description?: string;
}

// Project Types
export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  code_config?: Record<string, any>;
  scrum_config?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectInput {
  name: string;
  description?: string;
  code_config?: Record<string, any>;
  scrum_config?: Record<string, any>;
}

export interface UpdateProjectInput {
  name?: string;
  description?: string;
  code_config?: Record<string, any>;
  scrum_config?: Record<string, any>;
}

// API Response Types
export interface ListResponse<T> {
  items: T[];
  total: number;
}

// State Types
export interface WorkspaceState {
  items: Workspace[];
  currentWorkspace: Workspace | null;
  loading: boolean;
  error: string | null;
}

export interface ProjectState {
  items: Project[];
  currentProject: Project | null;
  loading: boolean;
  error: string | null;
}
