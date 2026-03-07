import { useAuth } from "react-oidc-context";
import { Button } from "@/components/ui/button";

export function Dashboard() {
  const auth = useAuth();

  const callHelloApi = async () => {
    try {
      const token = auth.user?.id_token;
      if (!token) {
        console.error("No ID token available");
        return;
      }

      const response = await fetch("http://localhost:8000/hello", {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });

      const result = await response.json();
      console.log("Hello API Response:", result);
      console.log("Status:", response.status);
    } catch (error) {
      console.error("Error calling hello API:", error);
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <div className="space-x-2">
          <Button variant="link" size="sm" onClick={callHelloApi}>Settings</Button>
          <Button size="sm" onClick={() => auth.removeUser()}>Sign Out</Button>
        </div>
      </div>

      <div className="space-y-4">
        <h2>Welcome, {auth.user?.profile.name || auth.user?.profile.email}!</h2>
        <p><strong>Email:</strong> {auth.user?.profile.email}</p>
        <p><strong>Phone:</strong> {auth.user?.profile.phone_number || "—"}</p>
      </div>
    </div>
  );
}
