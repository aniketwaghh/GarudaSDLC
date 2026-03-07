import { useAuth } from "react-oidc-context";
import { useNavigate } from "react-router-dom";
import { SignInButton } from "@/components/AuthButtons";
import { Button } from "@/components/ui/button";
import { CheckCircle2, Zap, Users, GitBranch, Brain, Shield, ArrowRight } from "lucide-react";

export function Home() {
  const auth = useAuth();
  const navigate = useNavigate();

  if (auth.isLoading) return <div className="p-8">Loading...</div>;

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
    <main className="bg-white">
      {/* Hero Section */}
      <section className="bg-gradient-to-b from-gray-50 to-white border-b">
        <div className="max-w-7xl mx-auto px-6 py-20 text-center">
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6 leading-tight">
            Transform client meetings into <span className="text-blue-600">working software</span>
          </h1>
          <p className="text-xl text-gray-600 max-w-4xl mx-auto mb-8 leading-relaxed">
            Garuda SDLC is an AI-native SDLC workspace that listens to your client calls, builds a project knowledge graph, 
            drafts your Jira tickets, coordinates "AI employees" on Slack, and keeps developers, testers, and DevOps fully in control.
          </p>
          <div className="flex gap-4 justify-center">
            {auth.isAuthenticated ? (
              <Button 
                size="lg" 
                onClick={() => navigate('/workspaces')}
                className="bg-blue-600 hover:bg-blue-700 text-white px-8"
              >
                Go to Garuda SDLC Console
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            ) : (
              <SignInButton />
            )}
          </div>
        </div>
      </section>

      {/* Problem and Pain */}
      <section className="py-20 bg-white border-b">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4 text-center">
            Service companies lose time and money
          </h2>
          <p className="text-lg text-gray-600 mb-12 text-center max-w-3xl mx-auto">
            Because the SDLC is still manual, scattered, and disconnected
          </p>
          <div className="grid md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-1">
                  <span className="text-red-600 font-bold">1</span>
                </div>
                <p className="text-gray-700 leading-relaxed">
                  Requirements live in scattered meeting notes and recordings no one re-watches.
                </p>
              </div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-1">
                  <span className="text-red-600 font-bold">2</span>
                </div>
                <p className="text-gray-700 leading-relaxed">
                  Translating meetings into Jira tickets, GitHub work, and releases is slow and manual.
                </p>
              </div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-1">
                  <span className="text-red-600 font-bold">3</span>
                </div>
                <p className="text-gray-700 leading-relaxed">
                  Priorities change in calls, but impact analysis and cleanup across Jira and code is painful.
                </p>
              </div>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-lg p-6">
              <div className="flex items-start gap-4">
                <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center flex-shrink-0 mt-1">
                  <span className="text-red-600 font-bold">4</span>
                </div>
                <p className="text-gray-700 leading-relaxed">
                  No single source of truth connects "what the client said" to "what we shipped".
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* What SDLC Does */}
      <section className="py-20 bg-gray-50 border-b">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-12 text-center">
            What SDLC does
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white rounded-lg p-8 shadow-sm border border-gray-200">
              <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center mb-4">
                <Brain className="w-6 h-6 text-blue-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">Meeting-to-knowledge hub</h3>
              <p className="text-gray-600 leading-relaxed">
                Your silent bot joins Google Meet, records audio/video, and stores it securely (HIPAA-ready stack). 
                It auto-generates transcripts, slide/screen summaries, mind maps, and a project knowledge graph, 
                all tied back to exact video timestamps.
              </p>
            </div>
            <div className="bg-white rounded-lg p-8 shadow-sm border border-gray-200">
              <div className="w-12 h-12 rounded-lg bg-green-100 flex items-center justify-center mb-4">
                <Users className="w-6 h-6 text-green-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">AI "employees", humans in control</h3>
              <p className="text-gray-600 leading-relaxed">
                Background agents act as AI Scrum helpers, product analysts, and dev assistants: 
                they propose Jira tickets, impact analysis, and documentation, but everything stays in draft 
                for Scrum Masters and leads to approve.
              </p>
            </div>
            <div className="bg-white rounded-lg p-8 shadow-sm border border-gray-200">
              <div className="w-12 h-12 rounded-lg bg-purple-100 flex items-center justify-center mb-4">
                <GitBranch className="w-6 h-6 text-purple-600" />
              </div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">From decisions to deployments</h3>
              <p className="text-gray-600 leading-relaxed">
                Agents talk over Slack like virtual teammates, coordinate work, and interact with Jira and GitHub via APIs. 
                Developers still code on feature branches, testers validate, and DevOps run safe pipelines with full rollback—your 
                process is optimized, not replaced.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Key Features */}
      <section className="py-20 bg-white border-b">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-12 text-center">
            Key features
          </h2>
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-start gap-4">
              <CheckCircle2 className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Workspace per client/project</h3>
                <p className="text-gray-600">
                  Persistent knowledge graph and RAG-style search across all meetings and artifacts.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <CheckCircle2 className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Traceable chunks</h3>
                <p className="text-gray-600">
                  Every summary, requirement, or decision is linked back to the original recording timeline as proof.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <CheckCircle2 className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Event-driven and scheduled agents</h3>
                <p className="text-gray-600">
                  Webhooks on meetings, Jira, and GitHub plus cron-style heartbeats so agents periodically re-check context.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-4">
              <CheckCircle2 className="w-6 h-6 text-green-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900 mb-2">Slack "agentic forum"</h3>
                <p className="text-gray-600">
                  Each agent has its own persona and collaborates in channels and threads, visible to the human team.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Value Proposition */}
      <section className="py-20 bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4 text-center">
            Value for service companies
          </h2>
          <p className="text-xl text-gray-600 mb-12 text-center max-w-3xl mx-auto">
            Scale delivery quality without scaling headcount at the same rate
          </p>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <Zap className="w-8 h-8 text-yellow-600 mb-3" />
              <h3 className="font-semibold text-gray-900 mb-2">Compress time</h3>
              <p className="text-sm text-gray-600">
                From "client said it in a call" to "feature shipped in production"
              </p>
            </div>
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <Users className="w-8 h-8 text-blue-600 mb-3" />
              <h3 className="font-semibold text-gray-900 mb-2">Reduce grunt work</h3>
              <p className="text-sm text-gray-600">
                In requirement grooming, ticket writing, impact analysis, and documentation
              </p>
            </div>
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <Shield className="w-8 h-8 text-green-600 mb-3" />
              <h3 className="font-semibold text-gray-900 mb-2">Perfect traceability</h3>
              <p className="text-sm text-gray-600">
                From client conversation to Jira ticket to Git commit
              </p>
            </div>
            <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
              <CheckCircle2 className="w-8 h-8 text-purple-600 mb-3" />
              <h3 className="font-semibold text-gray-900 mb-2">AI optimizes SDLC</h3>
              <p className="text-sm text-gray-600">
                While your people stay in charge—scale quality, not just headcount
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 bg-blue-600 text-white">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-6">
            Ready to transform your SDLC?
          </h2>
          <p className="text-xl mb-8 text-blue-100">
            Start turning client meetings into working software today.
          </p>
          {auth.isAuthenticated ? (
            <Button 
              size="lg" 
              onClick={() => navigate('/workspaces')}
              className="bg-white hover:bg-gray-100 text-blue-600 px-8"
            >
              Go to Garuda SDLC Console
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          ) : (
            <SignInButton />
          )}
        </div>
      </section>
    </main>
  );
}
