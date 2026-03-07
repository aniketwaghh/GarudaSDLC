import { Routes, Route } from "react-router-dom"
import { useAuth } from "react-oidc-context"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { Layout } from "@/components/Layout"
import { Home } from "@/pages/Home"
import { Workspaces } from "@/pages/Workspaces"
import { Projects } from "@/pages/Projects"
import { ProjectDetail } from "@/pages/ProjectDetail"
import { RequirementGathering } from "@/pages/RequirementGathering"
import { NotFound } from "@/pages/NotFound"

function App() {
  const auth = useAuth()

  if (auth.isLoading) {
    return (
      <div className="flex min-h-svh flex-col items-center justify-center">
        <div className="text-xl font-semibold">Loading...</div>
      </div>
    )
  }

  return (
    <Routes>
      {/* Routes with Layout (includes Header) */}
      <Route element={<Layout />}>
        {/* Public Home Route */}
        <Route path="/" element={<Home />} />

        {/* Protected Routes */}
        <Route
          path="/workspaces"
          element={
            <ProtectedRoute>
              <Workspaces />
            </ProtectedRoute>
          }
        />

        <Route
          path="/workspace/:workspaceId"
          element={
            <ProtectedRoute>
              <Projects />
            </ProtectedRoute>
          }
        />

        <Route
          path="/workspace/:workspaceId/project/:projectId"
          element={
            <ProtectedRoute>
              <ProjectDetail />
            </ProtectedRoute>
          }
        />

        <Route
          path="/workspace/:workspaceId/project/:projectId/requirements"
          element={
            <ProtectedRoute>
              <RequirementGathering />
            </ProtectedRoute>
          }
        />
      </Route>

      {/* Routes without Layout (404) */}
      <Route path="/404" element={<NotFound />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

export default App