import { useState, useRef, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Send, Loader2, FileText, Play, X } from "lucide-react";
import { apiClient, API_ENDPOINTS } from "@/config/api";
import { useToast } from "@/hooks/use-toast";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface RetrievedChunk {
  text: string;
  score: number;
  bot_id: string;
  meeting_id: string;
  start_time: string;
  end_time: string;
}

interface ChatResponse {
  message: string;
  retrieved_chunks: RetrievedChunk[];
  project_id: string;
  total_chunks: number;
}

export function Chat() {
  const { projectId } = useParams();
  const { toast } = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [retrievedChunks, setRetrievedChunks] = useState<RetrievedChunk[]>([]);
  const [videoPlayer, setVideoPlayer] = useState<{
    botId: string;
    startTime: string;
    endTime: string;
  } | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

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

  const playVideo = (botId: string, startTime: string, endTime: string) => {
    console.log("Playing video:", { botId, startTime, endTime });
    setVideoPlayer({ botId, startTime, endTime });
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
      setMessages([...newMessages, { role: "assistant", content: response.data.message }]);
      setRetrievedChunks(response.data.retrieved_chunks);

      toast({
        title: "Response received",
        description: `Used ${response.data.total_chunks} context chunks`,
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
    <div className="h-[calc(100vh-12rem)] flex gap-4">
      {/* Chat Column */}
      <div className="flex-1 flex flex-col">
        <Card className="flex-1 flex flex-col">
          <CardHeader className="border-b">
            <CardTitle className="text-lg">Requirements Chat</CardTitle>
            <p className="text-sm text-muted-foreground">
              Ask questions about your project requirements and meeting discussions
            </p>
          </CardHeader>
          
          <CardContent className="flex-1 flex flex-col p-0">
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
                    className={`max-w-[80%] rounded-lg px-4 py-2 ${
                      msg.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted"
                    }`}
                  >
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
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
      <div className="w-96">
        <Card className="h-full flex flex-col">
          <CardHeader className="border-b">
            <CardTitle className="text-lg flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Context Sources
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              {retrievedChunks.length > 0
                ? `${retrievedChunks.length} relevant transcript chunks`
                : "Context will appear here"}
            </p>
          </CardHeader>
          
          <CardContent className="flex-1 overflow-y-auto p-4 space-y-3">
            {retrievedChunks.length === 0 ? (
              <div className="text-center text-muted-foreground text-sm py-8">
                Ask a question to see relevant context
              </div>
            ) : (
              retrievedChunks.map((chunk, idx) => (
                <Card key={idx} className="bg-muted/50">
                  <CardHeader className="p-3 pb-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="text-xs">
                          #{idx + 1}
                        </Badge>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0"
                          onClick={() => playVideo(chunk.bot_id, chunk.start_time, chunk.end_time)}
                          title="Play video from this timestamp"
                        >
                          <Play className="h-3 w-3" />
                        </Button>
                      </div>
                      <Badge variant="secondary" className="text-xs">
                        Score: {chunk.score.toFixed(3)}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground space-y-1 mt-2">
                      <p>Meeting: {chunk.meeting_id.slice(0, 8)}...</p>
                      <p>Time: {chunk.start_time} - {chunk.end_time}</p>
                    </div>
                  </CardHeader>
                  <CardContent className="p-3 pt-0">
                    <p className="text-xs line-clamp-4">{chunk.text}</p>
                  </CardContent>
                </Card>
              ))
            )}
          </CardContent>
        </Card>
      </div>

      {/* Video Player Overlay */}
      {videoPlayer && (
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
                  src={API_ENDPOINTS.VIDEOS.STREAM(videoPlayer.botId)}
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
    </div>
  );
}
