import { useState, useRef, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Send, Loader2, FileText, Play, X, Download } from "lucide-react";
import { apiClient, API_ENDPOINTS } from "@/config/api";
import { useToast } from "@/hooks/use-toast";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface Reference {
  source_type: string; // 'meeting', 'document', 'langchain_doc'
  title: string;
  excerpt: string;
  metadata: Record<string, any>;
  relevance_score?: number | null;
}

interface ChatResponse {
  answer: string;
  references: Reference[];
  confidence: string;
  followup_questions: string[];
  project_id: string;
}

export function Chat() {
  const { projectId } = useParams();
  const { toast } = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [references, setReferences] = useState<Reference[]>([]);
  const [confidence, setConfidence] = useState<string>("");
  const [followupQuestions, setFollowupQuestions] = useState<string[]>([]);
  const [videoPlayer, setVideoPlayer] = useState<{
    botId: string;
    startTime: string;
    endTime: string;
    videoUrl?: string;
  } | null>(null);
  const [documentViewer, setDocumentViewer] = useState<{
    requirementId: string;
    filename: string;
    fileType: string;
    documentUrl: string;
    highlightText: string;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isLoadingVideo, setIsLoadingVideo] = useState(false);
  const [isLoadingDocument, setIsLoadingDocument] = useState(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Convert timestamp string (HH:MM:SS.mmm) to seconds
  const timeToSeconds = (timeStr: string): number => {
    const parts = timeStr.split(':');
    if (parts.length === 3) {
      const hours = parseInt(parts[0]);
      const minutes = parseInt(parts[1]);
      const seconds = parseFloat(parts[2]);
      return hours * 3600 + minutes * 60 + seconds;
    }
    return 0;
  };

  const playVideo = async (botId: string, startTime: string, endTime: string) => {
    console.log("Playing video:", { botId, startTime, endTime });
    
    setIsLoadingVideo(true);
    
    try {
      // Fetch presigned URL from backend
      const response = await apiClient.get(API_ENDPOINTS.VIDEOS.STREAM(botId));
      const videoUrl = response.data.video_url;
      
      if (!videoUrl) {
        throw new Error("No video URL returned from server");
      }
      
      setVideoPlayer({ botId, startTime, endTime, videoUrl });
    } catch (error: any) {
      console.error("Failed to fetch video URL:", error);
      toast({
        title: "Video loading error",
        description: error.response?.data?.detail || "Failed to load video URL from server",
        variant: "destructive",
      });
    } finally {
      setIsLoadingVideo(false);
    }
  };

  const downloadDocument = async (requirementId: string, filename: string) => {
    console.log("Downloading document:", { requirementId, filename });
    
    setIsLoadingDocument(true);
    
    try {
      // Get presigned URL for the document with download=true
      const response = await apiClient.get(API_ENDPOINTS.CUSTOM_REQUIREMENTS.VIEW(requirementId), {
        params: { download: true }
      });
      
      console.log("Download URL:", response.data.presigned_url);
      
      // Create a temporary link and trigger download
      const link = document.createElement('a');
      link.href = response.data.presigned_url;
      link.download = filename;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      toast({
        title: "Download Started",
        description: `Downloading ${filename}`,
      });
    } catch (error: any) {
      console.error("Error downloading document:", error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to download document",
        variant: "destructive",
      });
    } finally {
      setIsLoadingDocument(false);
    }
  };

  const closeVideo = () => {
    if (videoRef.current) {
      videoRef.current.pause();
      videoRef.current.src = "";
    }
    setVideoPlayer(null);
  };

  // Seek video when player opens
  useEffect(() => {
    if (videoPlayer && videoRef.current) {
      const video = videoRef.current;
      
      // Wait for video metadata to load before seeking
      const handleLoadedMetadata = () => {
        const startSeconds = timeToSeconds(videoPlayer.startTime);
        console.log("Seeking to:", startSeconds);
        video.currentTime = startSeconds;
        video.play().catch(err => {
          console.error("Error playing video:", err);
          toast({
            title: "Video playback error",
            description: "Failed to play video. Please check if the video file exists.",
            variant: "destructive",
          });
        });
      };
      
      const handleError = (e: Event) => {
        console.error("Video error:", e);
        toast({
          title: "Video loading error",
          description: "Failed to load video. Please check if the recording is available.",
          variant: "destructive",
        });
      };
      
      video.addEventListener("loadedmetadata", handleLoadedMetadata);
      video.addEventListener("error", handleError);
      
      return () => {
        video.removeEventListener("loadedmetadata", handleLoadedMetadata);
        video.removeEventListener("error", handleError);
      };
    }
  }, [videoPlayer, toast]);

  // Close video on ESC key
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && videoPlayer) {
        closeVideo();
      }
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [videoPlayer]);

  const sendMessage = async () => {
    if (!input.trim() || !projectId || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    
    // Add user message
    const newMessages = [...messages, { role: "user" as const, content: userMessage }];
    setMessages(newMessages);
    setIsLoading(true);

    try {
      const response = await apiClient.post<ChatResponse>(
        API_ENDPOINTS.CHAT,
        {
          message: userMessage,
          project_id: projectId,
          chat_history: messages,
          k: 5
        }
      );

      // Add assistant response
      setMessages([...newMessages, { role: "assistant", content: response.data.answer }]);
      setReferences(response.data.references);
      setConfidence(response.data.confidence);
      setFollowupQuestions(response.data.followup_questions);

      toast({
        title: "Response received",
        description: `${response.data.references.length} references | Confidence: ${response.data.confidence}`,
      });
    } catch (error: any) {
      console.error("Chat error:", error);
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to get response",
        variant: "destructive",
      });
      
      // Remove user message on error
      setMessages(messages);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex gap-4 p-4">
      {/* Chat Column */}
      <div className="flex-1 flex flex-col min-h-0">
        <Card className="h-full flex flex-col">
          <CardHeader className="border-b">
            <CardTitle className="text-lg">Requirements Chat</CardTitle>
            <p className="text-sm text-muted-foreground">
              Ask questions about your project requirements and meeting discussions
            </p>
          </CardHeader>
          
          <CardContent className="flex-1 flex flex-col p-0 overflow-hidden">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 && (
                <div className="text-center text-muted-foreground py-8">
                  <p className="text-lg mb-2">👋 Hi! I'm your AI assistant</p>
                  <p className="text-sm">Ask me anything about your project requirements</p>
                  <div className="mt-4 text-left max-w-md mx-auto space-y-2">
                    <p className="text-xs font-semibold">Example questions:</p>
                    <ul className="text-xs space-y-1 list-disc list-inside">
                      <li>What authentication methods were discussed?</li>
                      <li>What are the main features for the dashboard?</li>
                      <li>What database should we use?</li>
                      <li>What performance requirements were mentioned?</li>
                    </ul>
                  </div>
                </div>
              )}
              
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[80%] rounded-lg px-4 py-2 break-words ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    {msg.role === "user" ? (
                      <p className="text-sm whitespace-pre-wrap break-words">{msg.content}</p>
                    ) : (
                      <div className="text-sm prose prose-sm dark:prose-invert max-w-none prose-p:my-2 prose-ul:my-2 prose-ol:my-2 prose-li:my-0 prose-headings:my-2 break-words overflow-hidden">
                        <Markdown 
                          remarkPlugins={[remarkGfm]}
                          components={{
                            // Style code blocks
                            code: (props) => {
                              const { node, className, children, ...rest } = props;
                              const isInline = !className;
                              return isInline ? (
                                <code className="bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-xs" {...rest}>
                                  {children}
                                </code>
                              ) : (
                                <code className="block bg-gray-100 dark:bg-gray-800 p-2 rounded text-xs overflow-x-auto" {...rest}>
                                  {children}
                                </code>
                              );
                            },
                            // Style links
                            a: (props) => {
                              const { node, ...rest } = props;
                              return <a className="text-blue-600 dark:text-blue-400 hover:underline" {...rest} />;
                            },
                          }}
                        >
                          {msg.content}
                        </Markdown>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-muted rounded-lg px-4 py-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                  </div>
                </div>
              )}
              
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="border-t p-4">
              <div className="flex gap-2">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Ask a question about your requirements..."
                  disabled={isLoading}
                  className="flex-1"
                />
                <Button
                  onClick={sendMessage}
                  disabled={!input.trim() || isLoading}
                  size="icon"
                >
                  {isLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Context Column */}
      <div className="w-96 min-h-0">
        <Card className="h-full flex flex-col">
          <CardHeader className="border-b">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-4 w-4" />
              References & Context
            </CardTitle>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              {references.length > 0 && (
                <>
                  <span>{references.length} references</span>
                  {confidence && (
                    <Badge variant={confidence === 'high' ? 'default' : confidence === 'medium' ? 'secondary' : 'outline'} className="text-xs">
                      {confidence} confidence
                    </Badge>
                  )}
                </>
              )}
              {references.length === 0 && "References will appear here"}
            </div>
          </CardHeader>
          
          <CardContent className="flex-1 overflow-y-auto overflow-x-hidden p-4 space-y-4">
            {/* References */}
            {references.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-sm font-semibold">Sources</h4>
                {references.map((ref, idx) => {
                  const isMeeting = ref.source_type === 'meeting';
                  const isDocument = ref.source_type === 'document';
                  const isLangChainDoc = ref.source_type === 'langchain_doc';
                  
                  return (
                    <Card key={idx} className="bg-muted/50 overflow-hidden">
                      <CardHeader className="p-3 pb-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <Badge variant="outline" className="text-xs">
                              {isMeeting && '📹'}
                              {isDocument && '📄'}
                              {isLangChainDoc && '📚'}
                              {' '}#{idx + 1}
                            </Badge>
                            {isMeeting && ref.metadata.bot_id && ref.metadata.start_time && ref.metadata.end_time && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-6 w-6 p-0"
                                onClick={() => playVideo(ref.metadata.bot_id, ref.metadata.start_time, ref.metadata.end_time)}
                                title="Play video from this timestamp"
                              >
                                <Play className="h-3 w-3" />
                              </Button>
                            )}
                            {isDocument && ref.metadata.requirement_id && (
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-6 w-6 p-0"
                                onClick={() => downloadDocument(ref.metadata.requirement_id, ref.title)}
                                title="Download document"
                                disabled={isLoadingDocument}
                              >
                                {isLoadingDocument ? <Loader2 className="h-3 w-3 animate-spin" /> : <Download className="h-3 w-3" />}
                              </Button>
                            )}
                          </div>
                          {ref.relevance_score && (
                            <Badge variant="secondary" className="text-xs">
                              {(ref.relevance_score * 100).toFixed(0)}%
                            </Badge>
                          )}
                        </div>
                        <div className="text-xs font-medium mt-2 break-words">
                          {ref.title}
                        </div>
                        {Object.keys(ref.metadata).length > 0 && (
                          <div className="text-xs text-muted-foreground mt-1 break-words">
                            {isMeeting && (
                              <span>🕒 {ref.metadata.start_time} - {ref.metadata.end_time}</span>
                            )}
                            {isDocument && (
                              <span>📎 {ref.metadata.file_type?.toUpperCase()}</span>
                            )}
                            {isLangChainDoc && ref.metadata.url && (
                              <a href={ref.metadata.url} target="_blank" rel="noopener noreferrer" className="underline hover:text-primary break-all">
                                View docs
                              </a>
                            )}
                          </div>
                        )}
                      </CardHeader>
                      <CardContent className="p-3 pt-0">
                        <p className="text-xs line-clamp-3 italic break-words overflow-hidden">&ldquo;{ref.excerpt}&rdquo;</p>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
            
            {/* Follow-up Questions */}
            {followupQuestions.length > 0 && (
              <div className="space-y-2 pt-3 border-t">
                <h4 className="text-sm font-semibold">Follow-up Questions</h4>
                {followupQuestions.map((question, idx) => (
                  <Button
                    key={idx}
                    variant="outline"
                    size="sm"
                    className="w-full justify-start text-left h-auto py-2 px-3 text-xs break-words whitespace-normal"
                    onClick={() => {
                      setInput(question);
                    }}
                  >
                    {question}
                  </Button>
                ))}
              </div>
            )}
            
            {references.length === 0 && (
              <div className="text-center text-muted-foreground text-sm py-8">
                Ask a question to see references
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Video Player Overlay */}
      {videoPlayer && videoPlayer.videoUrl && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
          <div className="relative w-full max-w-4xl">
            <Button
              size="icon"
              variant="ghost"
              className="absolute -top-12 right-0 text-white hover:bg-white/20"
              onClick={closeVideo}
            >
              <X className="h-6 w-6" />
            </Button>
            <Card className="overflow-hidden">
              <CardContent className="p-0">
                <video
                  ref={videoRef}
                  controls
                  className="w-full"
                  preload="metadata"
                  crossOrigin="anonymous"
                  src={videoPlayer.videoUrl}
                  onLoadStart={() => console.log("Video load started")}
                  onLoadedData={() => console.log("Video data loaded")}
                >
                  Your browser does not support the video tag.
                </video>
                <div className="p-4 bg-muted">
                  <p className="text-sm">
                    <strong>Bot ID:</strong> {videoPlayer.botId}
                  </p>
                  <p className="text-sm">
                    <strong>Time:</strong> {videoPlayer.startTime} - {videoPlayer.endTime}
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Document Viewer Dialog */}
      <Dialog open={!!documentViewer} onOpenChange={(open) => !open && setDocumentViewer(null)}>
        <DialogContent className="max-w-6xl max-h-[95vh] h-[95vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>📄 {documentViewer?.filename}</DialogTitle>
            <DialogDescription>
              {documentViewer?.fileType?.toUpperCase()} Document
            </DialogDescription>
          </DialogHeader>
          <div className="flex-1 overflow-hidden">
            {/* Debug info */}
            {import.meta.env.DEV && documentViewer && (
              <div className="text-xs text-gray-500 p-2 bg-gray-100 mb-2 rounded overflow-auto">
                <div>File Type: {documentViewer.fileType}</div>
                <div>URL Length: {documentViewer.documentUrl?.length}</div>
                <div className="break-all">URL: {documentViewer.documentUrl}</div>
                <a 
                  href={documentViewer.documentUrl} 
                  target="_blank" 
                  rel="noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  Open in new tab (for testing)
                </a>
              </div>
            )}
            
            {documentViewer?.fileType === 'pdf' && documentViewer.documentUrl && (
              <iframe
                src={`${documentViewer.documentUrl}#view=FitH`}
                className="w-full h-full border-0 rounded"
                title={documentViewer.filename}
                onLoad={() => console.log("PDF iframe loaded successfully")}
                onError={(e) => console.error("PDF iframe error:", e)}
              />
            )}
            
            {documentViewer?.fileType === 'txt' && documentViewer.documentUrl && (
              <iframe
                src={documentViewer.documentUrl}
                className="w-full h-full border rounded bg-white p-4"
                title={documentViewer.filename}
                onLoad={() => console.log("TXT iframe loaded successfully")}
                onError={(e) => console.error("TXT iframe error:", e)}
              />
            )}
            
            {(documentViewer?.fileType === 'docx' || documentViewer?.fileType === 'doc') && (
              <div className="w-full h-full flex flex-col items-center justify-center gap-4 border rounded bg-gray-50">
                <FileText className="w-16 h-16 text-gray-400" />
                <div className="text-center space-y-2">
                  <p className="text-sm text-gray-600">
                    Word documents require Office 365 or Google Docs to view
                  </p>
                  <div className="flex gap-2 justify-center">
                    <Button
                      onClick={() => {
                        const officeUrl = `https://view.officeapps.live.com/op/embed.aspx?src=${encodeURIComponent(documentViewer.documentUrl)}`;
                        window.open(officeUrl, '_blank');
                      }}
                    >
                      Open in Office Online
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        const googleUrl = `https://docs.google.com/viewer?url=${encodeURIComponent(documentViewer.documentUrl)}&embedded=true`;
                        window.open(googleUrl, '_blank');
                      }}
                    >
                      Open in Google Docs
                    </Button>
                  </div>
                </div>
              </div>
            )}
            
            {/* Fallback for unsupported types or missing URL */}
            {documentViewer && !documentViewer.documentUrl && (
              <div className="w-full h-full flex items-center justify-center border rounded bg-gray-50">
                <p className="text-gray-600">Document URL is missing. Please try again.</p>
              </div>
            )}
            
            {documentViewer && documentViewer.documentUrl && 
             !['pdf', 'txt', 'docx', 'doc'].includes(documentViewer.fileType) && (
              <div className="w-full h-full flex flex-col items-center justify-center gap-4 border rounded bg-gray-50">
                <FileText className="w-16 h-16 text-gray-400" />
                <div className="text-center space-y-2">
                  <p className="text-sm text-gray-600">
                    File type "{documentViewer.fileType}" cannot be previewed in browser
                  </p>
                  <Button
                    onClick={() => window.open(documentViewer.documentUrl, '_blank')}
                  >
                    Download File
                  </Button>
                </div>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
      
      {/* Loading Overlay */}
      {isLoadingVideo && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="h-12 w-12 animate-spin text-white mx-auto mb-4" />
            <p className="text-white">Loading video...</p>
          </div>
        </div>
      )}
    </div>
  );
}
