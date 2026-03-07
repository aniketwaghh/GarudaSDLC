import { useAuth } from "react-oidc-context";
import { Button } from "@/components/ui/button";

export function SignInButton() {
  const auth = useAuth();
  return <Button onClick={() => auth.signinRedirect()}>Sign In</Button>;
}

export function SignOutButton() {
  const auth = useAuth();
  return <Button onClick={() => auth.removeUser()} variant="outline">Sign Out</Button>;
}
