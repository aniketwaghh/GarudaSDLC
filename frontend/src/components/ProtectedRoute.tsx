import { Navigate } from "react-router-dom";
import { useAuth } from "react-oidc-context";

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const auth = useAuth();
  console.log(auth);
  

  if (auth.isLoading) return <div className="p-8">Loading...</div>;
  if (!auth.isAuthenticated) return <Navigate to="/" replace />;

  return <>{children}</>;
}
