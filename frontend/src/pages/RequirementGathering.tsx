import { useState } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Label } from "@/components/ui/label";
import { Video, Calendar, Loader2 } from "lucide-react";
import { apiClient, API_ENDPOINTS } from "@/config/api";
import { useToast } from "@/hooks/use-toast";

export function RequirementGathering() {
  const { projectId } = useParams<{ projectId: string }>();
  const [meetingUrl, setMeetingUrl] = useState("");
  const [botName, setBotName] = useState("Garuda Bot");
  const [isLoading, setIsLoading] = useState(false);
  const { toast } = useToast();

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

    setIsLoading(true);

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
      setIsLoading(false);
    }
  };

  return (
    <main className="flex-1 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Requirement Gathering</h1>
          <p className="mt-2 text-gray-600">
            Record meetings to automatically gather requirements for your project
          </p>
        </div>

        <Tabs defaultValue="join-now" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="join-now">
              <Video className="w-4 h-4 mr-2" />
              Join Now
            </TabsTrigger>
            <TabsTrigger value="schedule">
              <Calendar className="w-4 h-4 mr-2" />
              Schedule
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
                    disabled={isLoading}
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
                    disabled={isLoading}
                  />
                  <p className="text-sm text-gray-500">
                    This name will appear in the meeting
                  </p>
                </div>

                <div className="flex justify-end">
                  <Button
                    onClick={handleJoinMeeting}
                    disabled={isLoading}
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {isLoading ? (
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
        </Tabs>
      </div>
    </main>
  );
}
