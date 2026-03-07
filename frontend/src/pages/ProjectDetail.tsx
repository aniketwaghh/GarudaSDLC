import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Video, Calendar, Loader2, FileUp } from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { fetchProjects, setCurrentProject } from "@/store/projectSlice";
import { fetchWorkspace } from "@/store/workspaceSlice";
import { apiClient, API_ENDPOINTS } from "@/config/api";
import { useToast } from "@/hooks/use-toast";

export function ProjectDetail() {
  const { workspaceId, projectId } = useParams();
  const dispatch = useAppDispatch();
  const { items: currentProject, loading, error } = useAppSelector((state) => state.projects);
  const { error: workspaceError } = useAppSelector((state) => state.workspaces);
  const { toast } = useToast();

  // Requirement Gathering state
  const [meetingUrl, setMeetingUrl] = useState("");
  const [botName, setBotName] = useState("Garuda Bot");
  const [isJoiningMeeting, setIsJoiningMeeting] = useState(false);

  useEffect(() => {
    if (workspaceId) {
      dispatch(fetchWorkspace(workspaceId));
      dispatch(fetchProjects({ workspaceId, skip: 0, limit: 100 })).then((action: any) => {
        if (action.payload?.items) {
          const projectsList = action.payload.items;
          if (projectId) {
            const project = projectsList.find((p: any) => p.id === projectId);
            if (project) {
              dispatch(setCurrentProject(project));
            }
          } else if (projectsList.length > 0) {
            dispatch(setCurrentProject(projectsList[0]));
          }
        }
      });
    }
  }, [workspaceId, projectId, dispatch]);

  const handleJoinMeeting = async () => {
    if (!meetingUrl.trim()) {
      toast({
        title: "Error",
        description: "Please enter a meeting URL",
        variant: "destructive",
      });
      return;
    }

    if (!projectId) {
      toast({
        title: "Error",
        description: "Project ID not found",
        variant: "destructive",
      });
      return;
    }

    setIsJoiningMeeting(true);

    try {
      const response = await apiClient.post(API_ENDPOINTS.MEETINGS.JOIN, {
        meeting_url: meetingUrl,
        bot_name: botName,
        project_id: projectId,
      });

      toast({
        title: "Success!",
        description: `Bot "${response.data.bot_name}" has been sent to the meeting`,
      });

      // Clear form
      setMeetingUrl("");
      setBotName("Garuda Bot");
    } catch (error: any) {
      toast({
        title: "Failed to join meeting",
        description: error.response?.data?.detail || error.message || "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsJoiningMeeting(false);
    }
  };

  return (
    <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Error Messages */}
        {(error || workspaceError) && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error || workspaceError}</p>
          </div>
        )}

        {loading ? (
          <div className="text-center py-12">
            <p className="text-gray-600">Loading project...</p>
          </div>
        ) : (
          <>

            {/* Main Tabs */}
            {currentProject && (
              <Tabs defaultValue="bots" className="space-y-6">
                <TabsList className="grid w-full grid-cols-5 bg-white border border-gray-200 p-1 shadow-sm">
                  <TabsTrigger value="bots" className="data-[state=active]:bg-gray-100">Bots</TabsTrigger>
                  <TabsTrigger value="requirement" className="data-[state=active]:bg-gray-100">Requirement Gathering</TabsTrigger>
                  <TabsTrigger value="knowledge" className="data-[state=active]:bg-gray-100">Knowledge Base</TabsTrigger>
                  <TabsTrigger value="chatbot" className="data-[state=active]:bg-gray-100">Chatbot</TabsTrigger>
                  <TabsTrigger value="config" className="data-[state=active]:bg-gray-100">Config</TabsTrigger>
                </TabsList>

                {/* Bots Tab */}
                <TabsContent value="bots">
                  <Card>
                    <CardHeader>
                      <CardTitle>Bots</CardTitle>
                      <CardDescription>Manage and configure your bots</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="text-center py-12">
                        <div className="text-4xl mb-4">🤖</div>
                        <p className="text-gray-600 mb-4">No bots created yet</p>
                        <p className="text-sm text-gray-500 mb-6">
                          Create a bot to start recording and transcribing meetings using a unified API.
                        </p>
                        <Button className="bg-gray-900 hover:bg-gray-800 text-white">+ Create Bot</Button>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Requirement Gathering Tab */}
                <TabsContent value="requirement">
                  <Tabs defaultValue="join-now" className="w-full">
                    <TabsList className="grid w-full grid-cols-3">
                      <TabsTrigger value="join-now">
                        <Video className="w-4 h-4 mr-2" />
                        Join Now
                      </TabsTrigger>
                      <TabsTrigger value="schedule">
                        <Calendar className="w-4 h-4 mr-2" />
                        Schedule
                      </TabsTrigger>
                      <TabsTrigger value="custom">
                        <FileUp className="w-4 h-4 mr-2" />
                        Custom
                      </TabsTrigger>
                    </TabsList>

                    <TabsContent value="join-now">
                      <Card>
                        <CardHeader>
                          <CardTitle>Join a Meeting Now</CardTitle>
                          <CardDescription>
                            Send a bot to join an active meeting and start recording
                          </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                          <div className="space-y-2">
                            <Label htmlFor="meeting-url">Meeting URL *</Label>
                            <Input
                              id="meeting-url"
                              type="url"
                              placeholder="https://zoom.us/j/123456789 or meet.google.com/xxx-yyyy-zzz"
                              value={meetingUrl}
                              onChange={(e) => setMeetingUrl(e.target.value)}
                              disabled={isJoiningMeeting}
                            />
                            <p className="text-sm text-gray-500">
                              Supports Zoom, Google Meet, Microsoft Teams, and more
                            </p>
                          </div>

                          <div className="space-y-2">
                            <Label htmlFor="bot-name">Bot Name</Label>
                            <Input
                              id="bot-name"
                              type="text"
                              placeholder="Garuda Bot"
                              value={botName}
                              onChange={(e) => setBotName(e.target.value)}
                              disabled={isJoiningMeeting}
                            />
                            <p className="text-sm text-gray-500">
                              This name will appear in the meeting
                            </p>
                          </div>

                          <div className="flex justify-end">
                            <Button
                              onClick={handleJoinMeeting}
                              disabled={isJoiningMeeting}
                              className="bg-blue-600 hover:bg-blue-700"
                            >
                              {isJoiningMeeting ? (
                                <>
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                  Joining...
                                </>
                              ) : (
                                <>
                                  <Video className="mr-2 h-4 w-4" />
                                  Join Meeting
                                </>
                              )}
                            </Button>
                          </div>

                          <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                            <h4 className="font-semibold text-blue-900 mb-2">How it works:</h4>
                            <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                              <li>Enter the meeting URL and bot name</li>
                              <li>Click "Join Meeting" to send the bot</li>
                              <li>The bot will join and start recording automatically</li>
                              <li>Recordings and transcripts will be saved to your project</li>
                            </ol>
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>

                    <TabsContent value="schedule">
                      <Card>
                        <CardHeader>
                          <CardTitle>Schedule Meeting Recording</CardTitle>
                          <CardDescription>
                            Schedule a bot to join a future meeting
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="text-center py-12 text-gray-500">
                            <Calendar className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                            <p className="text-lg font-medium">Coming Soon</p>
                            <p className="mt-2 text-sm">
                              Schedule recording feature will be available in a future update
                            </p>
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>

                    <TabsContent value="custom">
                      <Card>
                        <CardHeader>
                          <CardTitle>Upload Custom Documents</CardTitle>
                          <CardDescription>
                            Upload PDF documents and other files for requirement analysis
                          </CardDescription>
                        </CardHeader>
                        <CardContent>
                          <div className="text-center py-12 text-gray-500">
                            <FileUp className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                            <p className="text-lg font-medium">Coming Soon</p>
                            <p className="mt-2 text-sm">
                              Upload PDFs, Word documents, and other files to extract requirements
                            </p>
                          </div>
                        </CardContent>
                      </Card>
                    </TabsContent>
                  </Tabs>
                </TabsContent>

                {/* Knowledge Base Tab */}
                <TabsContent value="knowledge">
                  <Card>
                    <CardHeader>
                      <CardTitle>Knowledge Base</CardTitle>
                      <CardDescription>Manage project documentation and knowledge</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="text-center py-12">
                        <div className="text-4xl mb-4">📚</div>
                        <p className="text-gray-600 mb-4">Knowledge base is empty</p>
                        <p className="text-sm text-gray-500 mb-6">
                          Add documentation and knowledge articles for your team.
                        </p>
                        <Button className="bg-gray-900 hover:bg-gray-800 text-white">+ Add Knowledge Article</Button>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Chatbot Tab */}
                <TabsContent value="chatbot">
                  <Card>
                    <CardHeader>
                      <CardTitle>Chatbot</CardTitle>
                      <CardDescription>Configure and manage your project chatbot</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="text-center py-12">
                        <div className="text-4xl mb-4">💬</div>
                        <p className="text-gray-600 mb-4">Chatbot not configured</p>
                        <p className="text-sm text-gray-500 mb-6">
                          Set up a chatbot to assist with project inquiries and support.
                        </p>
                        <Button className="bg-gray-900 hover:bg-gray-800 text-white">+ Configure Chatbot</Button>
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>

                {/* Config Tab */}
                <TabsContent value="config">
                  <Card>
                    <CardHeader>
                      <CardTitle>Configuration</CardTitle>
                      <CardDescription>Configure code repository and integrations</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Code Config */}
                      {currentProject.code_config && Object.keys(currentProject.code_config).length > 0 ? (
                        <div>
                          <h3 className="font-semibold text-gray-900 mb-4">Code Configuration</h3>
                          <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                            {Object.entries(currentProject.code_config).map(([key, value]) => (
                              <div key={key} className="flex justify-between items-center">
                                <span className="text-sm font-medium text-gray-700">{key}:</span>
                                <Badge variant="secondary">{String(value)}</Badge>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="text-center py-8">
                          <p className="text-gray-600 mb-4">No code configuration</p>
                          <Button variant="outline">+ Configure Code Repo</Button>
                        </div>
                      )}

                      {/* Jira Config */}
                      {currentProject.scrum_config && Object.keys(currentProject.scrum_config).length > 0 ? (
                        <div>
                          <h3 className="font-semibold text-gray-900 mb-4">Scrum Configuration</h3>
                          <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                            {Object.entries(currentProject.scrum_config).map(([key, value]) => (
                              <div key={key} className="flex justify-between items-center">
                                <span className="text-sm font-medium text-gray-700">{key}:</span>
                                <Badge variant="outline">{String(value)}</Badge>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="text-center py-8">
                          <p className="text-gray-600 mb-4">No Jira configuration</p>
                          <Button variant="outline">+ Configure Jira</Button>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </TabsContent>
              </Tabs>
            )}
          </>
        )}
    </main>
  );
}
