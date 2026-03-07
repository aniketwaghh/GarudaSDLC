import { useAuth } from "react-oidc-context";
import { SignInButton } from "@/components/AuthButtons";
import { Navigate } from "react-router-dom";

export function Login() {
  const auth = useAuth();

  if (auth.isLoading) return <div className="p-8">Loading...</div>;
  if (auth.isAuthenticated) return <Navigate to="/workspaces" replace />;
  
  if (auth.error) {
    return (
      <div className="flex min-h-svh flex-col items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Auth Error</h1>
          <p className="text-red-600 mb-4">{auth.error.message}</p>
          <SignInButton />
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-svh flex-col items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-3xl font-bold">Sign In</h1>
        <p>Securely sign in with AWS Cognito</p>
        <SignInButton />
      </div>
    </div>
  );
}
