import { configureStore } from "@reduxjs/toolkit";
import workspaceReducer from "./workspaceSlice";
import projectReducer from "./projectSlice";

export const store = configureStore({
  reducer: {
    workspaces: workspaceReducer,
    projects: projectReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
