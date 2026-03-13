import { useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Video, Calendar, Loader2, FileUp, Trash2, Plus, Bot, Library, MessageSquare, Settings, FileText, LogOut } from "lucide-react";
import logo from "@/assets/logo.png";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import { fetchProjects, setCurrentProject } from "@/store/projectSlice";
import { fetchWorkspace } from "@/store/workspaceSlice";
import { apiClient, API_ENDPOINTS } from "@/config/api";
import { useToast } from "@/hooks/use-toast";
import { Chat } from "@/pages/Chat";
import { RequirementGathering } from "@/pages/RequirementGathering";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
  SidebarInset,
  SidebarHeader,
  SidebarFooter,
} from "@/components/ui/sidebar";
import { useAuth } from "react-oidc-context";

export function ProjectDetail() {
  const { workspaceId, projectId } = useParams();
  const dispatch = useAppDispatch();
  const auth = useAuth();
  const { items: currentProject, loading, error } = useAppSelector((state) => state.projects);
  const { error: workspaceError } = useAppSelector((state) => state.workspaces);
  const { toast } = useToast();

  // Active view state for sidebar navigation
  const [activeView, setActiveView] = useState<"bots" | "requirement" | "knowledge" | "chatbot" | "config">("bots");

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

  // Custom Requirements state
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedRequirements, setUploadedRequirements] = useState<any[]>([]);
  const [isLoadingRequirements, setIsLoadingRequirements] = useState(false);
  const [isUploadDialogOpen, setIsUploadDialogOpen] = useState(false);

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

  // Custom Requirements Functions
  const fetchCustomRequirements = async () => {
    if (!projectId) return;
    
    setIsLoadingRequirements(true);
    try {
      const response = await apiClient.get(API_ENDPOINTS.CUSTOM_REQUIREMENTS.LIST(projectId));
      setUploadedRequirements(response.data);
    } catch (error: any) {
      console.error("Failed to fetch requirements:", error);
      toast({
        title: "Error",
        description: "Failed to load uploaded documents",
        variant: "destructive",
      });
    } finally {
      setIsLoadingRequirements(false);
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
      setIsUploadDialogOpen(false);
      
      // Refresh requirements list
      fetchCustomRequirements();
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

  const handleDeleteRequirement = async (requirementId: string, filename: string) => {
    try {
      await apiClient.delete(API_ENDPOINTS.CUSTOM_REQUIREMENTS.DELETE(requirementId));
      toast({
        title: "Success!",
        description: `"${filename}" deleted successfully`,
      });
      fetchCustomRequirements();
    } catch (error: any) {
      toast({
        title: "Failed to delete document",
        description: error.response?.data?.detail || error.message || "An error occurred",
        variant: "destructive",
      });
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case 'pdf':
        return '📄';
      case 'docx':
      case 'doc':
        return '📝';
      case 'txt':
        return '📃';
      default:
        return '📄';
    }
  };

  // Load custom requirements on mount
  useEffect(() => {
    if (projectId) {
      fetchCustomRequirements();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

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
    <SidebarProvider defaultOpen={true}>
      <div className="flex h-screen w-full">
        <Sidebar collapsible="icon">
          <SidebarHeader className="border-b px-6 py-4 group-data-[collapsible=icon]:px-3">
            <div className="flex items-center gap-3 group-data-[collapsible=icon]:justify-center">
              <img src={logo} alt="Garuda SDLC" className="h-8 w-8 object-contain" />
              <div className="flex flex-col group-data-[collapsible=icon]:hidden">
                <span className="text-base font-semibold text-gray-900 leading-none">Garuda SDLC</span>
                {currentProject?.name && (
                  <span className="text-xs text-gray-500 leading-none mt-1">{currentProject.name}</span>
                )}
              </div>
            </div>
          </SidebarHeader>
          <SidebarContent>
            <SidebarGroup>
              <SidebarGroupContent>
                <SidebarMenu>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      onClick={() => setActiveView("bots")}
                      isActive={activeView === "bots"}
                      tooltip="Bots"
                    >
                      <Bot className="w-4 h-4" />
                      <span>Bots</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      onClick={() => setActiveView("requirement")}
                      isActive={activeView === "requirement"}
                      tooltip="Requirement Gathering"
                    >
                      <FileText className="w-4 h-4" />
                      <span>Requirements</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      onClick={() => setActiveView("knowledge")}
                      isActive={activeView === "knowledge"}
                      tooltip="Knowledge Base"
                    >
                      <Library className="w-4 h-4" />
                      <span>Knowledge Base</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      onClick={() => setActiveView("chatbot")}
                      isActive={activeView === "chatbot"}
                      tooltip="Chatbot"
                    >
                      <MessageSquare className="w-4 h-4" />
                      <span>Chatbot</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                  <SidebarMenuItem>
                    <SidebarMenuButton
                      onClick={() => setActiveView("config")}
                      isActive={activeView === "config"}
                      tooltip="Config"
                    >
                      <Settings className="w-4 h-4" />
                      <span>Config</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                </SidebarMenu>
              </SidebarGroupContent>
            </SidebarGroup>
          </SidebarContent>
          <SidebarFooter className="border-t">
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton
                  onClick={() => auth.removeUser()}
                  tooltip="Sign Out"
                  className="text-red-600 hover:text-red-700 hover:bg-red-50"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign Out</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarFooter>
        </Sidebar>

        <SidebarInset className="flex-1 overflow-auto">
          <main className="p-6">
            <div className="flex items-center gap-4 mb-6">
              <SidebarTrigger />
              <h6 className="text-base font-medium text-gray-900">
                {activeView === "bots" && "Bots"}
                {activeView === "requirement" && "Requirement Gathering"}
                {activeView === "knowledge" && "Knowledge Base"}
                {activeView === "chatbot" && "Chatbot"}
                {activeView === "config" && "Configuration"}
              </h6>
            </div>
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
            ) : currentProject && (
              <>
                {/* Bots View */}
                {activeView === "bots" && (
                  <div className="space-y-6">
                  
                    <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                      <div className="text-4xl mb-4">🤖</div>
                      <p className="text-gray-600 mb-4">No bots created yet</p>
                      <p className="text-sm text-gray-500 mb-6">
                        Create a bot to start recording and transcribing meetings using a unified API.
                      </p>
                      <Button className="bg-gray-900 hover:bg-gray-800 text-white">+ Create Bot</Button>
                    </div>
                  </div>
                )}

                {/* Requirement Gathering View */}
                {activeView === "requirement" && (
                  <RequirementGathering />
                )}

                {/* Knowledge Base View */}
                {activeView === "knowledge" && (
                  <div className="space-y-6">
                    <div>
                      <h2 className="text-2xl font-semibold text-gray-900">Knowledge Base</h2>
                      <p className="mt-1 text-sm text-gray-500">
                        Manage project documentation and knowledge
                      </p>
                    </div>
                    <div className="bg-white rounded-lg border border-gray-200 p-12 text-center">
                      <div className="text-4xl mb-4">📚</div>
                      <p className="text-gray-600 mb-4">Knowledge base is empty</p>
                      <p className="text-sm text-gray-500 mb-6">
                        Add documentation and knowledge articles for your team.
                      </p>
                      <Button className="bg-gray-900 hover:bg-gray-800 text-white">+ Add Knowledge Article</Button>
                    </div>
                  </div>
                )}

                {/* Chatbot View */}
                {activeView === "chatbot" && (
                  <Chat />
                )}

                {/* Config View */}
                {activeView === "config" && (
                  <div className="space-y-6">
                    <div>
                      <h2 className="text-2xl font-semibold text-gray-900">Configuration</h2>
                      <p className="mt-1 text-sm text-gray-500">
                        Configure code repository and integrations
                      </p>
                    </div>
                    <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-6">
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
                    </div>
                  </div>
                )}
              </>
            )}
          </main>
        </SidebarInset>
      </div>
    </SidebarProvider>
  );
}
