import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import type { PayloadAction } from "@reduxjs/toolkit";
import { workspaceService } from "@/services";
import type {
  Workspace,
  CreateWorkspaceInput,
  UpdateWorkspaceInput,
  WorkspaceState,
  ListResponse,
} from "@/types";

// Async Thunks
export const fetchWorkspaces = createAsyncThunk(
  "workspaces/fetchWorkspaces",
  async ({
    skip = 0,
    limit = 100,
  }: { skip?: number; limit?: number } = {}) => {
    return await workspaceService.list(skip, limit);
  }
);

export const fetchWorkspace = createAsyncThunk(
  "workspaces/fetchWorkspace",
  async (id: string) => {
    return await workspaceService.get(id);
  }
);

export const createWorkspace = createAsyncThunk(
  "workspaces/createWorkspace",
  async (data: CreateWorkspaceInput) => {
    return await workspaceService.create(data);
  }
);

export const updateWorkspace = createAsyncThunk(
  "workspaces/updateWorkspace",
  async ({ id, data }: { id: string; data: UpdateWorkspaceInput }) => {
    return await workspaceService.update(id, data);
  }
);

export const deleteWorkspace = createAsyncThunk(
  "workspaces/deleteWorkspace",
  async (id: string) => {
    await workspaceService.delete(id);
    return id;
  }
);

// Initial State
const initialState: WorkspaceState = {
  items: [],
  currentWorkspace: null,
  loading: false,
  error: null,
};

// Slice
const workspaceSlice = createSlice({
  name: "workspaces",
  initialState,
  reducers: {
    setCurrentWorkspace: (state, action: PayloadAction<Workspace | null>) => {
      state.currentWorkspace = action.payload;
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    // Fetch Workspaces
    builder
      .addCase(fetchWorkspaces.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        fetchWorkspaces.fulfilled,
        (state, action: PayloadAction<ListResponse<Workspace>>) => {
          state.loading = false;
          state.items = action.payload.items;
        }
      )
      .addCase(fetchWorkspaces.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch workspaces";
      });

    // Fetch Single Workspace
    builder
      .addCase(fetchWorkspace.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        fetchWorkspace.fulfilled,
        (state, action: PayloadAction<Workspace>) => {
          state.loading = false;
          state.currentWorkspace = action.payload;
        }
      )
      .addCase(fetchWorkspace.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to fetch workspace";
      });

    // Create Workspace
    builder
      .addCase(createWorkspace.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        createWorkspace.fulfilled,
        (state, action: PayloadAction<Workspace>) => {
          state.loading = false;
          state.items.push(action.payload);
        }
      )
      .addCase(createWorkspace.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to create workspace";
      });

    // Update Workspace
    builder
      .addCase(updateWorkspace.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        updateWorkspace.fulfilled,
        (state, action: PayloadAction<Workspace>) => {
          state.loading = false;
          const index = state.items.findIndex((w) => w.id === action.payload.id);
          if (index !== -1) {
            state.items[index] = action.payload;
          }
          state.currentWorkspace = action.payload;
        }
      )
      .addCase(updateWorkspace.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to update workspace";
      });

    // Delete Workspace
    builder
      .addCase(deleteWorkspace.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(
        deleteWorkspace.fulfilled,
        (state, action: PayloadAction<string>) => {
          state.loading = false;
          state.items = state.items.filter((w) => w.id !== action.payload);
          state.currentWorkspace = null;
        }
      )
      .addCase(deleteWorkspace.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || "Failed to delete workspace";
      });
  },
});

export const { setCurrentWorkspace, clearError } = workspaceSlice.actions;
export default workspaceSlice.reducer;
