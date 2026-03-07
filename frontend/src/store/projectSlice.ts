import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import { projectService } from "@/services";
import type {
  Project,
  CreateProjectInput,
  UpdateProjectInput,
  ProjectState,
  ListResponse,
} from "@/types";

// Async Thunks
export const fetchProjects = createAsyncThunk(
  "projects/fetchProjects",
  async ({
    workspaceId,
    skip = 0,
    limit = 100,
  }: { workspaceId: string; skip?: number; limit?: number }) => {
    return await projectService.list(workspaceId, skip, limit);
  }
);

export const fetchProject = createAsyncThunk(
  "projects/fetchProject",
  async ({ workspaceId, projectId }: { workspaceId: string; projectId: string }) => {
    return await projectService.get(workspaceId, projectId);
  }
);

export const createProject = createAsyncThunk(
  "projects/createProject",
  async ({
    workspaceId,
    data,
  }: { workspaceId: string; data: CreateProjectInput }) => {
    return await projectService.create(workspaceId, data);
  }
);

export const updateProject = createAsyncThunk(
  "projects/updateProject",
  async ({
    workspaceId,
    projectId,
    data,
  }: { workspaceId: string; projectId: string; data: UpdateProjectInput }) => {
    return await projectService.update(workspaceId, projectId, data);
  }
);

export const deleteProject = createAsyncThunk(
  "projects/deleteProject",
  async ({ workspaceId, projectId }: { workspaceId: string; projectId: string }) => {
    await projectService.delete(workspaceId, projectId);
    return projectId;
  }
);

// Initial State
const initialState: ProjectState = {
  items: [],
  currentProject: null,
  loading: false,
  error: null,
};

// Slice
const projectSlice = createSlice({
  name: "projects",
  initialState,
  reducers: {
    setCurrentProject: (state, action: PayloadAction<Project | null>) => {
      state.currentProject = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Fetch Projects
    builder
      .addCase(fetchProjects.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        fetchProjects.fulfilled,
        (state, action: PayloadAction<ListResponse<Project>>) => {
          state.loading = false;
          state.items = action.payload.items;
        }
      )
      .addCase(fetchProjects.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch projects";
      });

    // Fetch Single Project
    builder
      .addCase(fetchProject.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        fetchProject.fulfilled,
        (state, action: PayloadAction<Project>) => {
          state.loading = false;
          state.currentProject = action.payload;
        }
      )
      .addCase(fetchProject.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch project";
      });

    // Create Project
    builder
      .addCase(createProject.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        createProject.fulfilled,
        (state, action: PayloadAction<Project>) => {
          state.loading = false;
          state.items.push(action.payload);
        }
      )
      .addCase(createProject.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to create project";
      });

    // Update Project
    builder
      .addCase(updateProject.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        updateProject.fulfilled,
        (state, action: PayloadAction<Project>) => {
          state.loading = false;
          const index = state.items.findIndex((p) => p.id === action.payload.id);
          if (index !== -1) {
            state.items[index] = action.payload;
          }
          state.currentProject = action.payload;
        }
      )
      .addCase(updateProject.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to update project";
      });

    // Delete Project
    builder
      .addCase(deleteProject.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        deleteProject.fulfilled,
        (state, action: PayloadAction<string>) => {
          state.loading = false;
          state.items = state.items.filter((p) => p.id !== action.payload);
          state.currentProject = null;
        }
      )
      .addCase(deleteProject.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to delete project";
      });
  },
});

export const { setCurrentProject, clearError } = projectSlice.actions;
export default projectSlice.reducer;
