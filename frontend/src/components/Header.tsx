import { useAuth } from "react-oidc-context";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { LogOut, ArrowLeft } from "lucide-react";
import logo from "@/assets/logo.png";
import { SignInButton } from "@/components/AuthButtons";

interface HeaderProps {
  title?: string;
  subtitle?: string;
  showBack?: boolean;
  backPath?: string;
}

export function Header({ title, subtitle, showBack, backPath }: HeaderProps) {
  const auth = useAuth();
  const navigate = useNavigate();

  const handleBack = () => {
    if (backPath) {
      navigate(backPath);
    } else {
      navigate(-1);
    }
  };

  return (
    <header className="border-b backdrop-blur-md bg-white/70 sticky top-0 z-50 supports-[backdrop-filter]:bg-white/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-14 items-center justify-between">
          <div className="flex items-center gap-3">
            {showBack && auth.isAuthenticated && (
              <Button
                variant="ghost"
                size="icon"
                onClick={handleBack}
                title="Back"
                className="h-8 w-8 hover:bg-gray-100/50"
              >
                <ArrowLeft className="h-4 w-4 text-gray-700" />
              </Button>
            )}
            <img src={logo} alt="Garuda SDLC" className="h-8 w-8 object-contain" />
            <div className="flex flex-col">
              {title ? (
                <>
                  <span className="text-sm font-semibold text-gray-900 leading-none">{title}</span>
                  {subtitle && (
                    <span className="text-xs text-gray-500 leading-none mt-0.5">{subtitle}</span>
                  )}
                </>
              ) : (
                <span className="text-sm font-semibold text-gray-900">Garuda SDLC</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {auth.isAuthenticated ? (
              <Button 
                variant="ghost" 
                size="icon"
                onClick={() => auth.removeUser()}
                title="Sign Out"
                className="h-8 w-8 hover:bg-gray-100/50"
              >
                <LogOut className="h-4 w-4 text-gray-700" />
              </Button>
            ) : (
              <SignInButton />
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
