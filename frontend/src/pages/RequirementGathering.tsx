import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Video, Calendar, Loader2, Plus, FileText, ChevronDown, Filter, Upload, X, Trash2 } from "lucide-react";
import { apiClient, API_ENDPOINTS } from "@/config/api";
import { useToast } from "@/hooks/use-toast";

type RequirementType = "meet" | "custom";
type MeetingStatus = "scheduled" | "in_progress" | "completed" | "failed";

interface RequirementSession {
  id: string;
  type: RequirementType;
  title: string;
  status?: MeetingStatus;
  created_at: string;
  meeting_url?: string;
  bot_name?: string;
}

export function RequirementGathering() {
  const { projectId } = useParams<{ projectId: string }>();
  const [sessions, setSessions] = useState<RequirementSession[]>([]);
  const [filteredSessions, setFilteredSessions] = useState<RequirementSession[]>([]);
  const [filterType, setFilterType] = useState<RequirementType | "all">("all");
  
  // Dialog states
  const [showJoinDialog, setShowJoinDialog] = useState(false);
  const [showScheduleDialog, setShowScheduleDialog] = useState(false);
  const [showCustomDialog, setShowCustomDialog] = useState(false);
  
  // Form states
  const [meetingUrl, setMeetingUrl] = useState("");
  const [botName, setBotName] = useState("Garuda Bot");
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  const { toast } = useToast();

  // Schedule Meeting state
  const [scheduleMeetingUrl, setScheduleMeetingUrl] = useState("");
  const [scheduleBotName, setScheduleBotName] = useState("Garuda Bot");
  const [scheduleDate, setScheduleDate] = useState("");
  const [scheduleTime, setScheduleTime] = useState("10:00");
  const [scheduleRecurrence, setScheduleRecurrence] = useState("daily");
  const [isCreatingSchedule, setIsCreatingSchedule] = useState(false);

  // Custom Requirements state
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  // Delete animation state
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Load sessions
  useEffect(() => {
    loadSessions();
  }, [projectId]);

  // Filter sessions
  useEffect(() => {
    if (filterType === "all") {
      setFilteredSessions(sessions);
    } else {
      setFilteredSessions(sessions.filter(s => s.type === filterType));
    }
  }, [sessions, filterType]);

  const loadSessions = async () => {
    if (!projectId) return;
    
    setIsLoadingSessions(true);
    try {
      // Fetch all requirements (meetings + custom) from unified endpoint
      const response = await apiClient.get(API_ENDPOINTS.REQUIREMENTS.LIST_ALL(projectId));
      const allRequirements = response.data.map((req: any) => ({
        id: req.id,
        type: req.type as RequirementType,  // 'meet' or 'custom'
        title: req.title,
        status: req.status as MeetingStatus | undefined,
        created_at: req.created_at,
        meeting_url: req.meeting_url,
        bot_name: req.bot_name,
      }));
      
      setSessions(allRequirements);
    } catch (error: any) {
      console.error("Failed to load requirements:", error);
      toast({
        title: "Failed to load sessions",
        description: error.response?.data?.detail || error.message || "An error occurred",
        variant: "destructive",
      });
    } finally {
      setIsLoadingSessions(false);
    }
  };

  const getCronExpression = () => {
    if (!scheduleDate && scheduleRecurrence === "once") {
      return null;
    }

    const [hours, minutes] = scheduleTime.split(":").map(Number);

    // Convert local time to UTC for AWS EventBridge
    const localDateTime = new Date();
    localDateTime.setHours(hours, minutes, 0, 0);
    
    const utcHours = localDateTime.getUTCHours();
    const utcMinutes = localDateTime.getUTCMinutes();

    switch (scheduleRecurrence) {
      case "once": {
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
        return `cron(${utcMinutes} ${utcHours} * * ? *)`;
      case "weekdays":
        return `cron(${utcMinutes} ${utcHours} ? * MON-FRI *)`;
      case "weekly": {
        if (!scheduleDate) return `cron(${utcMinutes} ${utcHours} ? * MON *)`;
        const date = new Date(scheduleDate);
        date.setHours(hours, minutes, 0, 0);
        const days = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
        const dayOfWeek = days[date.getUTCDay()];
        return `cron(${utcMinutes} ${utcHours} ? * ${dayOfWeek} *)`;
      }
      case "monthly": {
        if (!scheduleDate) {
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

      // Clear form and close dialog
      setMeetingUrl("");
      setBotName("Garuda Bot");
      setShowJoinDialog(false);
      
      // Reload sessions
      loadSessions();
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
      await apiClient.post(API_ENDPOINTS.SCHEDULES.CREATE, {
        meeting_url: scheduleMeetingUrl,
        bot_name: scheduleBotName,
        project_id: projectId,
        cron_expression: cronExpression,
      });

      toast({
        title: "Success!",
        description: "Schedule created! Bot will join meeting at the specified time.",
      });

      // Clear form
      setScheduleMeetingUrl("");
      setScheduleBotName("Garuda Bot");
      setScheduleDate("");
      setScheduleTime("10:00");
      setScheduleRecurrence("daily");
      
      // Close dialog and reload sessions
      setShowScheduleDialog(false);
      loadSessions();
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

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      const fileArray = Array.from(files);
      
      // Validate file types
      const allowedTypes = ['.txt', '.pdf', '.docx', '.doc'];
      const validFiles = fileArray.filter(file => {
        const ext = '.' + file.name.split('.').pop()?.toLowerCase();
        return allowedTypes.includes(ext);
      });

      if (validFiles.length !== fileArray.length) {
        toast({
          title: "Invalid file type",
          description: "Only TXT, PDF, DOCX files are allowed",
          variant: "destructive",
        });
      }

      setSelectedFiles(prev => [...prev, ...validFiles]);
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleUploadFiles = async () => {
    if (selectedFiles.length === 0) {
      toast({
        title: "No files selected",
        description: "Please select at least one file to upload",
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

    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('project_id', projectId);
      
      // Add user email if available
      const auth = localStorage.getItem("oidc.user");
      if (auth) {
        try {
          const user = JSON.parse(auth);
          if (user?.profile?.email) {
            formData.append('user_email', user.profile.email);
          }
        } catch (e) {
          console.error("Failed to parse user data:", e);
        }
      }

      // Add all files
      selectedFiles.forEach(file => {
        formData.append('files', file);
      });

      const response = await apiClient.post(
        API_ENDPOINTS.CUSTOM_REQUIREMENTS.UPLOAD,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      const successCount = response.data.filter((r: any) => r.status === 'completed').length;
      const failedCount = response.data.length - successCount;

      toast({
        title: "Upload Complete!",
        description: `${successCount} file(s) processed successfully${failedCount > 0 ? `, ${failedCount} failed` : ''}`,
      });

      // Clear selected files
      setSelectedFiles([]);
      
      // Close the upload dialog
      setShowCustomDialog(false);
      
      // Reload sessions
      loadSessions();
    } catch (error: any) {
      toast({
        title: "Upload Failed",
        description: error.response?.data?.detail || error.message || "An error occurred during upload",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const handleDeleteSession = async (sessionId: string, sessionType: RequirementType, sessionTitle: string) => {
    if (!confirm(`Are you sure you want to delete "${sessionTitle}"?\n\nThis will permanently delete:\n- All recording files (video, audio, transcripts)\n- All vector embeddings\n- All database records\n\nThis action cannot be undone.`)) {
      return;
    }

    // Start delete animation
    setDeletingId(sessionId);

    try {
      if (sessionType === "custom") {
        await apiClient.delete(API_ENDPOINTS.CUSTOM_REQUIREMENTS.DELETE(sessionId));
        toast({
          title: "Deleted",
          description: `"${sessionTitle}" has been deleted successfully`,
        });
      } else if (sessionType === "meet") {
        await apiClient.delete(API_ENDPOINTS.MEETINGS.DELETE(sessionId));
        toast({
          title: "Deleted",
          description: `Meeting "${sessionTitle}" and all associated files have been deleted`,
        });
      }

      // Wait a moment before removing from list
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // Reload sessions
      loadSessions();
    } catch (error: any) {
      toast({
        title: "Failed to delete",
        description: error.response?.data?.detail || error.message || "An error occurred",
        variant: "destructive",
      });
    } finally {
      setDeletingId(null);
    }
  };

  const getStatusBadge = (status?: MeetingStatus) => {
    const variants: Record<MeetingStatus, { variant: any; label: string }> = {
      scheduled: { variant: "secondary", label: "Scheduled" },
      in_progress: { variant: "default", label: "In Progress" },
      completed: { variant: "outline", label: "Completed" },
      failed: { variant: "destructive", label: "Failed" },
    };
    
    // Default to completed for custom requirements without status
    const config = status ? variants[status] : { variant: "outline", label: "Uploaded" };
    return <Badge variant={config.variant}>{config.label}</Badge>;
  };

  const getTypeBadge = (type: RequirementType) => {
    return type === "meet" ? (
      <Badge variant="default" className="bg-blue-100 text-blue-800 hover:bg-blue-100">
        <Video className="w-3 h-3 mr-1" />
        Meet
      </Badge>
    ) : (
      <Badge variant="default" className="bg-purple-100 text-purple-800 hover:bg-purple-100">
        <FileText className="w-3 h-3 mr-1" />
        Custom
      </Badge>
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    }).format(date);
  };

  return (
    <main className="flex-1 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6">
        

        {/* Filters and Actions Bar */}
        <div className="flex items-center justify-between border-b border-gray-200 pb-4">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">Filter by:</span>
            </div>
            <div className="flex gap-2">
              <Button
                variant={filterType === "all" ? "default" : "outline"}
                size="sm"
                onClick={() => setFilterType("all")}
              >
                All
              </Button>
              <Button
                variant={filterType === "meet" ? "default" : "outline"}
                size="sm"
                onClick={() => setFilterType("meet")}
              >
                <Video className="w-3 h-3 mr-1" />
                Meet
              </Button>
              <Button
                variant={filterType === "custom" ? "default" : "outline"}
                size="sm"
                onClick={() => setFilterType("custom")}
              >
                <FileText className="w-3 h-3 mr-1" />
                Custom
              </Button>
            </div>
            <div className="text-sm text-gray-500 border-l border-gray-300 pl-4">
              {filteredSessions.length} session{filteredSessions.length !== 1 ? 's' : ''}
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button className="bg-blue-600 hover:bg-blue-700">
                <Plus className="w-4 h-4 mr-2" />
                Add Requirement
                <ChevronDown className="w-4 h-4 ml-2" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>Meet</DropdownMenuLabel>
              <DropdownMenuItem onClick={() => setShowJoinDialog(true)}>
                <Video className="w-4 h-4 mr-2" />
                Join Now
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setShowScheduleDialog(true)}>
                <Calendar className="w-4 h-4 mr-2" />
                Schedule
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setShowCustomDialog(true)}>
                <FileText className="w-4 h-4 mr-2" />
                Custom
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        {/* Sessions Table */}
        <div className="bg-white rounded-lg border border-gray-200">
          {isLoadingSessions ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p className="text-lg font-medium text-gray-900">No sessions yet</p>
              <p className="mt-2 text-sm text-gray-500">
                Start gathering requirements by clicking "Add Requirement" above
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Type</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSessions.map((session) => (
                  <TableRow 
                    key={session.id}
                    className={deletingId === session.id ? 'animate-delete-shimmer' : ''}
                    style={{
                      border: deletingId === session.id ? '3px dotted rgba(239, 68, 68, 0.6)' : undefined,
                      borderRadius: deletingId === session.id ? '8px' : undefined,
                    }}
                  >
                    <TableCell>{getTypeBadge(session.type)}</TableCell>
                    <TableCell className="font-medium">{session.title}</TableCell>
                    <TableCell>{getStatusBadge(session.status)}</TableCell>
                    <TableCell className="text-gray-500">
                      {formatDate(session.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button variant="ghost" size="sm" disabled={deletingId === session.id}>
                          View Details
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteSession(session.id, session.type, session.title)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                          disabled={deletingId !== null}
                        >
                          {deletingId === session.id ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                          ) : (
                            <Trash2 className="w-4 h-4" />
                          )}
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        {/* Join Meeting Dialog */}
        <Dialog open={showJoinDialog} onOpenChange={setShowJoinDialog}>
          <DialogContent className="sm:max-w-[550px]">
            <DialogHeader>
              <DialogTitle>Join a Meeting Now</DialogTitle>
              <DialogDescription>
                Send a bot to join an active meeting and start recording
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-6 py-4">
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

              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h4 className="font-semibold text-blue-900 mb-2">How it works:</h4>
                <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                  <li>Enter the meeting URL and bot name</li>
                  <li>Click "Join Meeting" to send the bot</li>
                  <li>The bot will join and start recording automatically</li>
                  <li>Recordings and transcripts will be saved to your project</li>
                </ol>
              </div>

              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={() => setShowJoinDialog(false)}
                  disabled={isLoading}
                >
                  Cancel
                </Button>
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
            </div>
          </DialogContent>
        </Dialog>

        {/* Schedule Meeting Dialog */}
        <Dialog open={showScheduleDialog} onOpenChange={setShowScheduleDialog}>
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
                  placeholder="https://zoom.us/j/123456789 or meet.google.com/xxx-yyyy-zzz"
                  value={scheduleMeetingUrl}
                  onChange={(e) => setScheduleMeetingUrl(e.target.value)}
                  disabled={isCreatingSchedule}
                />
                <p className="text-sm text-gray-500">
                  Supports Zoom, Google Meet, Microsoft Teams, and more
                </p>
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
                </div>
              )}

              {scheduleRecurrence !== "once" && (
                <div className="space-y-2">
                  <Label htmlFor="schedule-time-recurring">Time *</Label>
                  <Input
                    id="schedule-time-recurring"
                    type="time"
                    value={scheduleTime}
                    onChange={(e) => setScheduleTime(e.target.value)}
                    disabled={isCreatingSchedule}
                  />
                  <p className="text-sm text-gray-500">
                    Time is in your local timezone
                  </p>
                </div>
              )}

              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h4 className="font-semibold text-blue-900 mb-2">How it works:</h4>
                <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                  <li>Enter the meeting URL and schedule details</li>
                  <li>Bot will automatically join at the specified time(s)</li>
                  <li>Recordings will be saved to your project</li>
                  <li>You can manage schedules from the main project view</li>
                </ol>
              </div>

              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={() => setShowScheduleDialog(false)}
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

        {/* Custom Requirements Dialog */}
        <Dialog open={showCustomDialog} onOpenChange={setShowCustomDialog}>
          <DialogContent className="sm:max-w-[600px]">
            <DialogHeader>
              <DialogTitle>Upload Custom Requirements</DialogTitle>
              <DialogDescription>
                Upload documents containing project requirements (PDF, Word, Text files)
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-6 py-4">
              <div className="space-y-4">
                <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-blue-400 transition-colors">
                  <input
                    type="file"
                    id="file-upload"
                    multiple
                    accept=".txt,.pdf,.docx,.doc"
                    onChange={handleFileSelect}
                    className="hidden"
                    disabled={isUploading}
                  />
                  <label
                    htmlFor="file-upload"
                    className="cursor-pointer flex flex-col items-center"
                  >
                    <Upload className="w-12 h-12 text-gray-400 mb-3" />
                    <span className="text-sm font-medium text-gray-700">Click to upload files</span>
                    <span className="text-xs text-gray-500 mt-1">or drag and drop</span>
                    <span className="text-xs text-gray-400 mt-2">PDF, DOCX, TXT (max 10MB each)</span>
                  </label>
                </div>

                {selectedFiles.length > 0 && (
                  <div className="space-y-2">
                    <Label>Selected Files ({selectedFiles.length})</Label>
                    <div className="max-h-48 overflow-y-auto space-y-2 border border-gray-200 rounded-lg p-3">
                      {selectedFiles.map((file, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-2 bg-gray-50 rounded hover:bg-gray-100"
                        >
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <FileText className="w-4 h-4 text-gray-500 flex-shrink-0" />
                            <span className="text-sm truncate" title={file.name}>
                              {file.name}
                            </span>
                            <span className="text-xs text-gray-400 flex-shrink-0">
                              {formatFileSize(file.size)}
                            </span>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveFile(index)}
                            disabled={isUploading}
                            className="flex-shrink-0 h-8 w-8 p-0"
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                <h4 className="font-semibold text-blue-900 mb-2">How it works:</h4>
                <ol className="text-sm text-blue-800 space-y-1 list-decimal list-inside">
                  <li>Upload requirement documents (PDFs, Word docs, text files)</li>
                  <li>Documents are automatically processed and indexed</li>
                  <li>Content becomes searchable via the chatbot</li>
                  <li>AI can reference these documents when answering questions</li>
                </ol>
              </div>

              <div className="flex justify-end gap-3">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowCustomDialog(false);
                    setSelectedFiles([]);
                  }}
                  disabled={isUploading}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleUploadFiles}
                  disabled={isUploading || selectedFiles.length === 0}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 h-4 w-4" />
                      Upload {selectedFiles.length > 0 ? `(${selectedFiles.length})` : ''}
                    </>
                  )}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </main>
  );
}
