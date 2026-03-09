import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Video, Calendar, Loader2, FileUp, Trash2, Plus } from "lucide-react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { fetchProjects, setCurrentProject } from "@/store/projectSlice";
import { fetchWorkspace } from "@/store/workspaceSlice";
import { apiClient, API_ENDPOINTS } from "@/config/api";
import { useToast } from "@/hooks/use-toast";
import { Chat } from "@/pages/Chat";

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

  // Schedule Meeting state
  const [scheduleMeetingUrl, setScheduleMeetingUrl] = useState("");
  const [scheduleBotName, setScheduleBotName] = useState("Garuda Bot");
  const [scheduleDate, setScheduleDate] = useState("");
  const [scheduleTime, setScheduleTime] = useState("10:00");
  const [scheduleRecurrence, setScheduleRecurrence] = useState("daily");
  const [isCreatingSchedule, setIsCreatingSchedule] = useState(false);
  const [schedules, setSchedules] = useState<any[]>([]);
  const [isLoadingSchedules, setIsLoadingSchedules] = useState(false);
  const [isScheduleDialogOpen, setIsScheduleDialogOpen] = useState(false);
  const [showLocalTime, setShowLocalTime] = useState(true); // Toggle for UTC/Local time display

  // Convert date/time to AWS EventBridge cron expression
  const fetchSchedules = async () => {
    if (!projectId) return;
    
    setIsLoadingSchedules(true);
    try {
      const response = await apiClient.get(`${API_ENDPOINTS.SCHEDULES.LIST}?project_id=${projectId}`);
      
      // Filter out expired one-time schedules
      const now = new Date();
      const filtered = response.data.filter((schedule: any) => {
        // Parse cron expression to check if it's a one-time schedule
        const cronMatch = schedule.cron_expression.match(/cron\((\d+) (\d+) (\d+) (\d+) \? (\d+)\)/);
        
        if (cronMatch) {
          // One-time schedule: cron(minute hour day month ? year)
          const [, minute, hour, day, month, year] = cronMatch;
          const scheduleDate = new Date(Date.UTC(
            parseInt(year),
            parseInt(month) - 1,
            parseInt(day),
            parseInt(hour),
            parseInt(minute)
          ));
          
          // Filter out if schedule time has passed
          return scheduleDate > now;
        }
        
        // Keep recurring schedules
        return true;
      });
      
      setSchedules(filtered);
    } catch (error: any) {
      console.error("Failed to fetch schedules:", error);
    } finally {
      setIsLoadingSchedules(false);
    }
  };

  const getCronExpression = () => {
    if (!scheduleDate && scheduleRecurrence === "once") {
      return null;
    }

    const [hours, minutes] = scheduleTime.split(":").map(Number);

    // Convert local time to UTC for AWS EventBridge
    // EventBridge Scheduler interprets cron expressions in UTC
    const localDateTime = new Date();
    localDateTime.setHours(hours, minutes, 0, 0);
    
    // Get UTC hours and minutes
    const utcHours = localDateTime.getUTCHours();
    const utcMinutes = localDateTime.getUTCMinutes();

    switch (scheduleRecurrence) {
      case "once": {
        // One-time schedule: cron(minute hour day month ? year)
        // For once schedule, we need to consider the full date with timezone
        const date = new Date(scheduleDate);
        date.setHours(hours, minutes, 0, 0);
        
        const utcDay = date.getUTCDate();
        const utcMonth = date.getUTCMonth() + 1;
        const utcYear = date.getUTCFullYear();
        const utcHour = date.getUTCHours();
        const utcMin = date.getUTCMinutes();
        
        return `cron(${utcMin} ${utcHour} ${utcDay} ${utcMonth} ? ${utcYear})`;
      }
      case "daily":
        // Daily: cron(minute hour * * ? *)
        return `cron(${utcMinutes} ${utcHours} * * ? *)`;
      case "weekdays":
        // Weekdays (Mon-Fri): cron(minute hour ? * MON-FRI *)
        return `cron(${utcMinutes} ${utcHours} ? * MON-FRI *)`;
      case "weekly": {
        // Weekly on the same day: cron(minute hour ? * DAY *)
        if (!scheduleDate) return `cron(${utcMinutes} ${utcHours} ? * MON *)`;
        const date = new Date(scheduleDate);
        date.setHours(hours, minutes, 0, 0);
        const days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
        const dayOfWeek = days[date.getUTCDay()];
        return `cron(${utcMinutes} ${utcHours} ? * ${dayOfWeek} *)`;
      }
      case "monthly": {
        // Monthly on the same day: cron(minute hour day * ? *)
        if (!scheduleDate) {
          // For no date, use current day but with UTC time
          const date = new Date();
          const utcDay = date.getUTCDate();
          return `cron(${utcMinutes} ${utcHours} ${utcDay} * ? *)`;
        }
        const date = new Date(scheduleDate);
        date.setHours(hours, minutes, 0, 0);
        const utcDay = date.getUTCDate();
        return `cron(${utcMinutes} ${utcHours} ${utcDay} * ? *)`;
      }
      default:
        return `cron(${utcMinutes} ${utcHours} * * ? *)`;
    }
  };

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

  useEffect(() => {
    if (projectId) {
      fetchSchedules();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

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

  const handleScheduleMeeting = async () => {
    if (!scheduleMeetingUrl.trim()) {
      toast({
        title: "Error",
        description: "Please enter a meeting URL",
        variant: "destructive",
      });
      return;
    }

    const cronExpression = getCronExpression();
    if (!cronExpression) {
      toast({
        title: "Error",
        description: scheduleRecurrence === "once" 
          ? "Please select a date for one-time schedule"
          : "Please enter valid schedule details",
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

    setIsCreatingSchedule(true);

    try {
      const response = await apiClient.post(API_ENDPOINTS.SCHEDULES.CREATE, {
        meeting_url: scheduleMeetingUrl,
        bot_name: scheduleBotName,
        project_id: projectId,
        cron_expression: cronExpression,
      });

      toast({
        title: "Success!",
        description: `Schedule created! Bot will join meeting at the specified time.`,
      });

      // Clear form
      setScheduleMeetingUrl("");
      setScheduleBotName("Garuda Bot");
      setScheduleDate("");
      setScheduleTime("10:00");
      setScheduleRecurrence("daily");
      
      // Close dialog and refresh schedules
      setIsScheduleDialogOpen(false);
      fetchSchedules();
    } catch (error: any) {
      toast({
        title: "Failed to create schedule",
        description: error.response?.data?.detail || error.message || "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsCreatingSchedule(false);
    }
  };

  const handleDeleteSchedule = async (scheduleId: string) => {
    try {
      await apiClient.delete(API_ENDPOINTS.SCHEDULES.DELETE(scheduleId));
      toast({
        title: "Success!",
        description: "Schedule deleted successfully",
      });
      fetchSchedules();
    } catch (error: any) {
      toast({
        title: "Failed to delete schedule",
        description: error.response?.data?.detail || error.message || "An error occurred",
        variant: "destructive",
      });
    }
  };

  const formatCronExpression = (cron: string, useLocalTime: boolean = false) => {
    // Parse cron expression and return human-readable format
    const cronMatch = cron.match(/cron\((\d+) (\d+) (.+?) (.+?) \? (.+?)\)/);
    if (!cronMatch) return cron;

    const [, minute, hour, day, month, dayOfWeek] = cronMatch;
    let displayHour = parseInt(hour);
    let displayMinute = parseInt(minute);
    let timeZoneLabel = "UTC";

    // Convert UTC to local time if requested
    if (useLocalTime) {
      const utcDate = new Date();
      utcDate.setUTCHours(displayHour, displayMinute, 0, 0);
      displayHour = utcDate.getHours();
      displayMinute = utcDate.getMinutes();
      timeZoneLabel = "Local";
    }

    const timeStr = `${displayHour.toString().padStart(2, '0')}:${displayMinute.toString().padStart(2, '0')} ${timeZoneLabel}`;

    // One-time schedule (has year)
    if (dayOfWeek.match(/^\d{4}$/)) {
      if (useLocalTime) {
        // For one-time schedules, convert the full date/time
        const utcDate = new Date(Date.UTC(
          parseInt(dayOfWeek),
          parseInt(month) - 1,
          parseInt(day),
          parseInt(hour),
          parseInt(minute)
        ));
        const localDateStr = utcDate.toLocaleDateString('en-US', { month: 'numeric', day: 'numeric', year: 'numeric' });
        const localTimeStr = utcDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
        return `Once on ${localDateStr} at ${localTimeStr} Local`;
      }
      return `Once on ${month}/${day}/${dayOfWeek} at ${timeStr}`;
    }
    
    // Recurring schedules
    if (day === '*' && month === '*') return `Daily at ${timeStr}`;
    if (day === '?' && month === '*' && dayOfWeek === 'MON-FRI') return `Weekdays at ${timeStr}`;
    if (day === '?' && month === '*') return `Weekly on ${dayOfWeek} at ${timeStr}`;
    if (day !== '*' && month === '*') return `Monthly on day ${day} at ${timeStr}`;
    
    return cron;
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
                          <div className="flex flex-row items-center justify-between">
                            <div>
                              <CardTitle>Scheduled Meetings</CardTitle>
                              <CardDescription>
                                Manage automated bot recordings for recurring meetings
                              </CardDescription>
                            </div>
                            <Dialog open={isScheduleDialogOpen} onOpenChange={setIsScheduleDialogOpen}>
                            <DialogTrigger asChild>
                              <Button className="bg-blue-600 hover:bg-blue-700">
                                <Plus className="mr-2 h-4 w-4" />
                                Schedule Meeting
                              </Button>
                            </DialogTrigger>
                            <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
                              <DialogHeader>
                                <DialogTitle>Schedule Meeting Recording</DialogTitle>
                                <DialogDescription>
                                  Schedule a bot to join meetings automatically
                                </DialogDescription>
                              </DialogHeader>
                              <div className="space-y-4 py-4">
                                <div className="space-y-2">
                                  <Label htmlFor="schedule-meeting-url">Meeting URL *</Label>
                                  <Input
                                    id="schedule-meeting-url"
                                    type="url"
                                    placeholder="https://zoom.us/j/123456789"
                                    value={scheduleMeetingUrl}
                                    onChange={(e) => setScheduleMeetingUrl(e.target.value)}
                                    disabled={isCreatingSchedule}
                                  />
                                </div>

                                <div className="space-y-2">
                                  <Label htmlFor="schedule-bot-name">Bot Name</Label>
                                  <Input
                                    id="schedule-bot-name"
                                    type="text"
                                    placeholder="Garuda Bot"
                                    value={scheduleBotName}
                                    onChange={(e) => setScheduleBotName(e.target.value)}
                                    disabled={isCreatingSchedule}
                                  />
                                </div>

                                <div className="space-y-2">
                                  <Label htmlFor="schedule-recurrence">Recurrence *</Label>
                                  <Select
                                    value={scheduleRecurrence}
                                    onValueChange={setScheduleRecurrence}
                                    disabled={isCreatingSchedule}
                                  >
                                    <SelectTrigger id="schedule-recurrence">
                                      <SelectValue placeholder="Select recurrence" />
                                    </SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="once">One Time Only</SelectItem>
                                      <SelectItem value="daily">Daily</SelectItem>
                                      <SelectItem value="weekdays">Weekdays (Mon-Fri)</SelectItem>
                                      <SelectItem value="weekly">Weekly</SelectItem>
                                      <SelectItem value="monthly">Monthly</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>

                                {scheduleRecurrence === "once" && (
                                  <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                      <Label htmlFor="schedule-date">Date *</Label>
                                      <Input
                                        id="schedule-date"
                                        type="date"
                                        value={scheduleDate}
                                        onChange={(e) => setScheduleDate(e.target.value)}
                                        disabled={isCreatingSchedule}
                                        min={new Date().toISOString().split('T')[0]}
                                      />
                                    </div>
                                    <div className="space-y-2">
                                      <Label htmlFor="schedule-time">Time *</Label>
                                      <Input
                                        id="schedule-time"
                                        type="time"
                                        value={scheduleTime}
                                        onChange={(e) => setScheduleTime(e.target.value)}
                                        disabled={isCreatingSchedule}
                                      />
                                    </div>
                                    <p className="text-sm text-gray-500 col-span-2">
                                      Select date and time in your local timezone
                                    </p>
                                  </div>
                                )}

                                {(scheduleRecurrence === "weekly" || scheduleRecurrence === "monthly") && (
                                  <div className="grid grid-cols-2 gap-4">
                                    <div className="space-y-2">
                                      <Label htmlFor="schedule-start-date">Starting From (Optional)</Label>
                                      <Input
                                        id="schedule-start-date"
                                        type="date"
                                        value={scheduleDate}
                                        onChange={(e) => setScheduleDate(e.target.value)}
                                        disabled={isCreatingSchedule}
                                        min={new Date().toISOString().split('T')[0]}
                                      />
                                    </div>
                                    <div className="space-y-2">
                                      <Label htmlFor="schedule-time">Time *</Label>
                                      <Input
                                        id="schedule-time"
                                        type="time"
                                        value={scheduleTime}
                                        onChange={(e) => setScheduleTime(e.target.value)}
                                        disabled={isCreatingSchedule}
                                      />
                                    </div>
                                    <p className="text-sm text-gray-500 col-span-2">
                                      {scheduleRecurrence === "weekly" 
                                        ? "Select date for day of week and time"
                                        : "Select date for day of month and time"}
                                    </p>
                                  </div>
                                )}

                                {(scheduleRecurrence === "daily" || scheduleRecurrence === "weekdays") && (
                                  <div className="space-y-2">
                                    <Label htmlFor="schedule-time">Time *</Label>
                                    <Input
                                      id="schedule-time"
                                      type="time"
                                      value={scheduleTime}
                                      onChange={(e) => setScheduleTime(e.target.value)}
                                      disabled={isCreatingSchedule}
                                    />
                                    <p className="text-sm text-gray-500">
                                      Enter time in your local timezone
                                    </p>
                                  </div>
                                )}

                                <div className="flex justify-end gap-2">
                                  <Button
                                    variant="outline"
                                    onClick={() => setIsScheduleDialogOpen(false)}
                                    disabled={isCreatingSchedule}
                                  >
                                    Cancel
                                  </Button>
                                  <Button
                                    onClick={handleScheduleMeeting}
                                    disabled={isCreatingSchedule}
                                    className="bg-blue-600 hover:bg-blue-700"
                                  >
                                    {isCreatingSchedule ? (
                                      <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        Creating...
                                      </>
                                    ) : (
                                      <>
                                        <Calendar className="mr-2 h-4 w-4" />
                                        Create Schedule
                                      </>
                                    )}
                                  </Button>
                                </div>
                              </div>
                            </DialogContent>
                          </Dialog>
                          </div>
                        </CardHeader>
                        <CardContent>
                          {isLoadingSchedules ? (
                            <div className="flex items-center justify-center py-8">
                              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                            </div>
                          ) : schedules.length === 0 ? (
                            <div className="text-center py-12">
                              <Calendar className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                              <h3 className="text-lg font-semibold text-gray-900 mb-2">No Scheduled Meetings</h3>
                              <p className="text-gray-500 mb-4">
                                Schedule a bot to automatically join your recurring meetings
                              </p>
                              <Button
                                onClick={() => setIsScheduleDialogOpen(true)}
                                className="bg-blue-600 hover:bg-blue-700"
                              >
                                <Plus className="mr-2 h-4 w-4" />
                                Schedule Your First Meeting
                              </Button>
                            </div>
                          ) : (
                            <div className="space-y-3">
                              <div className="flex items-center justify-end">
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => setShowLocalTime(!showLocalTime)}
                                  className="text-sm"
                                >
                                  {showLocalTime ? "🌍 Local Time" : "🌐 UTC Time"}
                                </Button>
                              </div>
                              <div className="overflow-x-auto">
                              <table className="w-full">
                                <thead>
                                  <tr className="border-b">
                                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Meeting URL</th>
                                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Bot Name</th>
                                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Schedule</th>
                                    <th className="text-left py-3 px-4 font-semibold text-gray-700">Status</th>
                                    <th className="text-right py-3 px-4 font-semibold text-gray-700">Actions</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {schedules.map((schedule) => (
                                    <tr key={schedule.id} className="border-b hover:bg-gray-50">
                                      <td className="py-3 px-4">
                                        <a
                                          href={schedule.meeting_url}
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="text-blue-600 hover:underline truncate block max-w-xs"
                                        >
                                          {schedule.meeting_url}
                                        </a>
                                      </td>
                                      <td className="py-3 px-4 text-gray-700">{schedule.bot_name}</td>
                                      <td className="py-3 px-4 text-sm text-gray-600">
                                        {formatCronExpression(schedule.cron_expression, showLocalTime)}
                                      </td>
                                      <td className="py-3 px-4">
                                        <Badge variant={schedule.status === "enabled" ? "default" : "secondary"}>
                                          {schedule.status}
                                        </Badge>
                                      </td>
                                      <td className="py-3 px-4 text-right">
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          onClick={() => handleDeleteSchedule(schedule.id)}
                                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                        >
                                          <Trash2 className="h-4 w-4" />
                                        </Button>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                              </div>
                            </div>
                          )}
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
                <TabsContent value="chatbot" className="mt-0">
                  <Chat />
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
