"use client";

import React, { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  BatteryCharging,
  LayoutDashboard,
  UploadCloud,
  FileText,
  LogOut,
  PhoneCall,
  Clock,
  Globe,
  Settings,
  AlertTriangle,
  Play,
  Pause,
  Search,
  Download,
  Trash2,
  CheckCircle2,
  Loader2,
  FileAudio,
  User,
  Info,
  ChevronRight,
  ChevronDown,
  Database,
  Brain,
  ShieldAlert,
  ThumbsUp,
  ThumbsDown,
  Minus,
  Zap,
  MessageSquare,
  ArrowLeft,
} from "lucide-react";

// AI Analysis result shape
interface AnalysisResult {
  summary: string;
  main_concern: string;
  outcome: string;
  action_needed: string;
  what_happened?: string;
  issue_detected: boolean;
  issue_type: string | null;
  severity: string | null;
  all_issues: { issue_type: string; severity: string }[];
  sentiment: "Positive" | "Neutral" | "Negative";
  sentiment_score: number;
  analysed: boolean;
}

interface Segment {
  id: number;
  start: number;
  end: number;
  text: string;
  speaker?: string;
}

interface Transcript {
  id: string;
  audio_file_id: string;
  text: string;
  language?: string;
  words_count: number;
  duration: number;
  segments?: Segment[];
  translated_text?: string;           // Full English translation
  translated_segments?: Segment[];    // Per-segment English translations
  analysis?: AnalysisResult;
  created_at: string;
}

interface AudioFile {
  id: string;
  filename: string;
  file_size: number;
  duration?: number;
  mime_type: string;
  status: "pending" | "processing" | "completed" | "failed";
  error_message?: string;
  created_at: string;
  transcript?: Transcript;
}

export default function Dashboard() {
  const router = useRouter();
  
  // Auth state
  const [username, setUsername] = useState<string>("");
  const [token, setToken] = useState<string | null>(null);
  
  // Active Tab
  const [activeTab, setActiveTab] = useState<"dashboard" | "upload" | "viewer">("dashboard");
  
  // Data list and active item
  const [audioFiles, setAudioFiles] = useState<AudioFile[]>([]);
  const [activeAudioFile, setActiveAudioFile] = useState<AudioFile | null>(null);
  const [loadingList, setLoadingList] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  
  // Search and filters
  const [searchQuery, setSearchQuery] = useState("");
  const [transcriptSearchQuery, setTranscriptSearchQuery] = useState("");
  const [expandedDates, setExpandedDates] = useState<Record<string, boolean>>({});
  const [selectedCategory, setSelectedCategory] = useState<string>("Support Issues");
  const [selectedSubcategory, setSelectedSubcategory] = useState<string>("All");

  const toggleDateGroup = (dateStr: string) => {
    setExpandedDates((prev) => ({
      ...prev,
      [dateStr]: !prev[dateStr],
    }));
  };
  
  // Upload Page States
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [audioPreviewUrl, setAudioPreviewUrl] = useState<string | null>(null);

  const [customPrompt, setCustomPrompt] = useState("");
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState<string>("");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);

  // Audio Player Sync in Transcript Viewer
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const [playbackSpeed, setPlaybackSpeed] = React.useState(1);
  const [audioStreamUrl, setAudioStreamUrl] = useState<string | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  // Helper to split a transcript segment list into alternating turns
  const getChatMessages = (segments: Segment[], duration: number) => {
    if (!segments || segments.length === 0) return [];
    
    // If we have actual diarized multi-segments (more than 1 segment)
    if (segments.length > 1) {
      return segments.map((seg, idx) => {
        const isAgent = seg.speaker?.toLowerCase().includes("agent") || 
                        seg.speaker?.toLowerCase().includes("support") ||
                        (seg.speaker && !seg.speaker.toLowerCase().includes("customer") && idx % 2 !== 0);
        return {
          id: seg.id,
          isAgent: !!isAgent,
          speaker: isAgent ? "Agent" : "Customer",
          text: seg.text,
          start: seg.start,
          end: seg.end
        };
      });
    }

    const fullText = segments[0].text;
    
    // Check if the text contains explicit speaker prefixes (e.g. "Customer:", "Support:", "Agent:")
    const speakerRegex = /(Customer|Support|Agent|User|Speaker\s*\d+)\s*:/gi;
    if (speakerRegex.test(fullText)) {
      // Reset regex index
      speakerRegex.lastIndex = 0;
      const parts = fullText.split(speakerRegex);
      // parts will be: [leading_text, speaker_1, text_1, speaker_2, text_2, ...]
      const messages = [];
      let currentIdx = 0;
      
      // Calculate total characters for timing distribution
      let totalChars = 0;
      for (let i = 2; i < parts.length; i += 2) {
        if (parts[i]) totalChars += parts[i].trim().length;
      }
      
      let elapsedSeconds = 0;
      
      for (let i = 1; i < parts.length; i += 2) {
        const rawSpeaker = parts[i];
        const rawText = parts[i+1] ? parts[i+1].trim() : "";
        if (!rawText) continue;
        
        const isAgent = rawSpeaker.toLowerCase().includes("support") || 
                        rawSpeaker.toLowerCase().includes("agent");
        
        // Distribute duration based on message length
        const msgLen = rawText.length;
        const msgDuration = totalChars > 0 ? (msgLen / totalChars) * duration : duration;
        
        messages.push({
          id: currentIdx++,
          isAgent,
          speaker: isAgent ? "Agent" : "Customer",
          text: rawText,
          start: elapsedSeconds,
          end: elapsedSeconds + msgDuration
        });
        
        elapsedSeconds += msgDuration;
      }
      return messages;
    }

    // Fallback: if we only have 1 single segment with the entire wall of text and NO speaker prefixes
    const sentences = fullText.match(/[^.!?]+[.!?]+(\s+|$)/g) || [fullText];
    
    const messages = [];
    let isAgent = false;
    const timePerSentence = duration / Math.max(sentences.length, 1);
    
    for (let i = 0; i < sentences.length; i++) {
      const text = sentences[i].trim();
      if (!text) continue;
      
      const lowerText = text.toLowerCase();
      // Heuristic detection for Agent vs Customer turns
      const isAgentPhrase = 
        lowerText.includes("tell me") || 
        lowerText.includes("car model") || 
        lowerText.includes("please wait") || 
        lowerText.includes("checking") || 
        lowerText.includes("wait in the line") || 
        lowerText.includes("tell me the otp") || 
        lowerText.includes("you are charged") || 
        lowerText.includes("go to the profile") || 
        lowerText.includes("transaction history");
        
      const isCustomerPhrase =
        lowerText.includes("we have gone to") ||
        lowerText.includes("reached") ||
        lowerText.includes("disconnected") ||
        lowerText.includes("402 server stop") ||
        lowerText.includes("402 stop") ||
        lowerText.includes("don't have my") ||
        lowerText.includes("wallet balance") ||
        lowerText.includes("took out the plug") ||
        lowerText.includes("received an otp") ||
        lowerText.includes("received") ||
        lowerText.includes("minus 4");

      if (isAgentPhrase) {
        isAgent = true;
      } else if (isCustomerPhrase) {
        isAgent = false;
      } else {
        // Alternate turns on question marks or every 2 sentences
        if (i > 0 && (sentences[i - 1].includes("?") || i % 2 === 0)) {
          isAgent = !isAgent;
        }
      }
      
      messages.push({
        id: i,
        isAgent,
        speaker: isAgent ? "Agent" : "Customer",
        text,
        start: i * timePerSentence,
        end: (i + 1) * timePerSentence
      });
    }
    return messages;
  };

  // Check auth and redirect on mount
  useEffect(() => {
    const storedToken = localStorage.getItem("oneplug_token");
    const storedUsername = localStorage.getItem("oneplug_username") || "Employee";
    
    if (!storedToken) {
      router.push("/login");
    } else {
      queueMicrotask(() => {
        setToken(storedToken);
        setUsername(storedUsername);
      });
    }
  }, [router]);

  // Fetch audios list on tab selection
  useEffect(() => {
    if (token) {
      fetchAudioFiles();
    }
  }, [token]);

  // Auto-refresh processing transcripts periodically
  useEffect(() => {
    if (!token) return;
    
    const hasProcessing = audioFiles.some(
      f => f.status === "pending" || f.status === "processing"
    );
    
    if (hasProcessing) {
      const interval = setInterval(() => {
        fetchAudioFiles();
      }, 4000);
      return () => clearInterval(interval);
    }
  }, [audioFiles, token]);

  useEffect(() => {
    return () => {
      if (audioStreamUrl) URL.revokeObjectURL(audioStreamUrl);
    };
  }, [audioStreamUrl]);

  function handleLogout() {
    localStorage.removeItem("oneplug_token");
    localStorage.removeItem("oneplug_username");
    router.push("/login");
  }

  async function fetchAudioFiles() {
    if (!token) return;
    setLoadingList(true);
    const apiBase = process.env.NEXT_PUBLIC_API_URL || `http://${window.location.hostname}:8002`;
    try {
      const res = await fetch(`${apiBase}/api/v1/transcribe/list`, {
        cache: "no-store",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        const data = await res.json();
        setAudioFiles(data);
      } else if (res.status === 401) {
        handleLogout();
      }
    } catch (e) {
      console.error("Error fetching calls:", e);
    } finally {
      setLoadingList(false);
    }
  }

  const loadTranscriptDetails = async (fileId: string) => {
    if (!token) return;
    setLoadingDetail(true);
    setActiveTab("viewer");
    if (audioStreamUrl) {
      URL.revokeObjectURL(audioStreamUrl);
      setAudioStreamUrl(null);
    }
    const apiBase = process.env.NEXT_PUBLIC_API_URL || `http://${window.location.hostname}:8002`;
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [res, audioResponse] = await Promise.all([
        fetch(`${apiBase}/api/v1/transcribe/file/${fileId}`, {
          cache: "no-store",
          headers,
        }),
        fetch(`${apiBase}/api/v1/transcribe/audio/${fileId}`, { headers }),
      ]);
      if (res.ok) {
        const data = await res.json();
        setActiveAudioFile(data);
        if (audioResponse.ok) {
          setAudioStreamUrl(URL.createObjectURL(await audioResponse.blob()));
        } else {
          setAudioStreamUrl(null);
        }
        // Clear search queries
        setTranscriptSearchQuery("");
      }
    } catch (e) {
      console.error("Error loading transcript details:", e);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDeleteTranscript = async (e: React.MouseEvent, fileId: string) => {
    e.stopPropagation();
    if (!token) return;
    
    if (!confirm("Are you sure you want to permanently delete this transcript and audio metadata?")) {
      return;
    }

    const apiBase = process.env.NEXT_PUBLIC_API_URL || `http://${window.location.hostname}:8002`;
    try {
      const res = await fetch(`${apiBase}/api/v1/transcribe/delete/${fileId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (res.ok) {
        setAudioFiles(prev => prev.filter(file => file.id !== fileId));
        if (activeAudioFile?.id === fileId) {
          setActiveAudioFile(null);
        }
      }
    } catch (e) {
      console.error("Error deleting transcript:", e);
    }
  };

  // Drag and drop events
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processSelectedFile(e.target.files[0]);
    }
  };

  const processSelectedFile = (file: File) => {
    const allowed = [".mp3", ".wav", ".m4a", ".ogg", ".flac"];
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    
    if (!allowed.includes(ext)) {
      setUploadError(`Unsupported file format. Supported formats: ${allowed.join(", ")}`);
      setSelectedFile(null);
      setAudioPreviewUrl(null);
      return;
    }
    
    setUploadError(null);
    setSelectedFile(file);
    
    // Create an audio preview URL
    const url = URL.createObjectURL(file);
    setAudioPreviewUrl(url);
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !token) return;

    setIsUploading(true);
    setUploadProgress(0);
    setUploadStage("Uploading file to server...");
    setUploadError(null);
    setUploadSuccess(false);

    const formData = new FormData();
    formData.append("file", selectedFile);

    if (customPrompt) {
      formData.append("prompt", customPrompt);
    }

    const apiBase = process.env.NEXT_PUBLIC_API_URL || `http://${window.location.hostname}:8002`;
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${apiBase}/api/v1/transcribe/upload`, true);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);

    // Track upload progress
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        setUploadProgress(percent);
        if (percent === 100) {
          setUploadStage("File uploaded. Initiating speech-to-text...");
        }
      }
    };

    xhr.onload = () => {
      setIsUploading(false);
      if (xhr.status === 202) {
        setUploadSuccess(true);
        setSelectedFile(null);
        setAudioPreviewUrl(null);
        setCustomPrompt("");
        // Refresh list
        fetchAudioFiles();
        // Redirect to dashboard tab to watch progress
        setTimeout(() => {
          setActiveTab("dashboard");
          setUploadSuccess(false);
        }, 1500);
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          setUploadError(err.detail || "Transcription upload failed.");
        } catch (e) {
          setUploadError("Server returned an error. Make sure backend is running.");
        }
      }
    };

    xhr.onerror = () => {
      setIsUploading(false);
      setUploadError("Network connection error. Failed to reach FastAPI backend.");
    };

    xhr.send(formData);
  };

  // Jump audio player to specific time
  const handleJumpToTime = (seconds: number) => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.currentTime = seconds;
      audioPlayerRef.current.play();
      setIsPlaying(true);
    }
  };

  // Export functions
  const downloadText = () => {
    if (!activeAudioFile?.transcript?.analysis) return;
    const txt = activeAudioFile.transcript.analysis.what_happened || "No AI explanation available.";
    const blob = new Blob([txt], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${activeAudioFile.filename}_explanation.txt`;
    a.click();
  };

  const downloadJSON = () => {
    if (!activeAudioFile?.transcript) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(activeAudioFile.transcript, null, 2));
    const a = document.createElement("a");
    a.href = dataStr;
    a.download = `${activeAudioFile.filename}_transcript.json`;
    a.click();
  };

  const downloadCSV = () => {
    if (!activeAudioFile?.transcript?.segments) return;
    const segments = activeAudioFile.transcript.segments;
    let csvContent = "data:text/csv;charset=utf-8,Speaker,Start,End,Text\n";
    
    segments.forEach(seg => {
      const row = `"${seg.speaker || 'Unknown'}","${seg.start}","${seg.end}","${seg.text.replace(/"/g, '""')}"`;
      csvContent += row + "\n";
    });
    
    const encodedUri = encodeURI(csvContent);
    const a = document.createElement("a");
    a.href = encodedUri;
    a.download = `${activeAudioFile.filename}_transcript.csv`;
    a.click();
  };

  // Helper to format timestamps
  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? "0" : ""}${secs}`;
  };

  // Helper to format bytes
  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  // Classification helper for files
  const getCallCategory = (file: AudioFile) => {
    const text = (file.transcript?.text || "").toLowerCase();
    const summary = (file.transcript?.analysis?.summary || "").toLowerCase();
    const concern = (file.transcript?.analysis?.main_concern || "").toLowerCase();
    const sentiment = file.transcript?.analysis?.sentiment || "Neutral";
    const issues = file.transcript?.analysis?.issues || [];
    
    // 1. Junk / Hang-ups Check (Evaluated first to bypass support keyword matches)
    const cleanText = text.trim();
    const junkWords = ["hello", "hello hello", "audible", "sir can you hear me", "recorded", "voicemail", "not available", "thank you", "okay"];
    const isJunk = cleanText === "" || 
                   cleanText.split(" ").length <= 4 || 
                   junkWords.some(kw => cleanText === kw || cleanText.includes("person is not available")) ||
                   concern === "none" ||
                   summary === "none" ||
                   file.filename.toLowerCase().startsWith("none");
    
    if (isJunk) {
      return { category: "General & Noise", subcategory: "Junk / Hang-ups", icon: "" };
    }

    // 2. Partnership Enquiries Check
    const franchiseKeywords = ["franchise", "enquiry", "branch", "invest", "dealer", "partner", "placement", "space for", "rent my land", "land offering", "site selection", "install charger"];
    if (franchiseKeywords.some(kw => text.includes(kw) || summary.includes(kw) || concern.includes(kw))) {
      return { category: "Partnership Enquiries", subcategory: "", icon: "" };
    }
    
    // 2. Support Issues Check
    const hasChargingIssue = ["not charging", "no charging", "charger not working", "charger not", "not working", "disconnected", "session ended early", "session cut", "session stopped", "power cut", "402", "error", "failed", "stuck", "not starting", "slow charging", "signal", "offline", "unplug", "plugged in but"].some(kw => text.includes(kw) || concern.includes(kw) || summary.includes(kw));
    const hasPaymentIssue = ["money deducted", "deducted", "refund", "not refunded", "double charge", "charged twice", "payment failed", "wallet", "transaction failed", "money not", "amount deducted"].some(kw => text.includes(kw) || concern.includes(kw) || summary.includes(kw));
    const hasAppBug = ["app crash", "crashing", "app not opening", "otp not", "otp not coming", "login failed", "cannot login", "app bug", "app error", "not loading", "stuck on", "black screen", "rfid not", "rfid card not", "card not working"].some(kw => text.includes(kw) || concern.includes(kw) || summary.includes(kw));
    const hasPricingComplaint = ["cost", "price", "rate", "tariff", "pricing", "eb rate"].some(kw => text.includes(kw) || concern.includes(kw) || summary.includes(kw)) && ["high", "expensive", "increase", "costly", "too much", "heavy"].some(kw => text.includes(kw) || concern.includes(kw) || summary.includes(kw));
    const hasDbFlag = file.status === "failed" || file.error_message;
    const hasTechnicalIssue = hasChargingIssue || hasPaymentIssue || hasAppBug;
    
    if (hasDbFlag || hasTechnicalIssue || hasPricingComplaint) {
      let sub = "Hardware & Charging";
      if (hasPricingComplaint) {
        sub = "Pricing & Tariffs";
      } else if (["payment", "billing", "refund", "wallet", "deducted", "double", "money", "charged", "debit", "transaction"].some(kw => text.includes(kw) || concern.includes(kw) || summary.includes(kw))) {
        sub = "Payment & Billing";
      } else if (["app", "otp", "login", "loading", "crash", "map", "qr", "scan", "account"].some(kw => text.includes(kw) || concern.includes(kw) || summary.includes(kw))) {
        sub = "App & Login";
      }
      return { category: "Support Issues", subcategory: sub, icon: "" };
    }
    
    // 3. Positive Feedback Check
    if (sentiment === "Positive" || ["good", "satisfied", "excellent", "great", "nice", "fine"].some(kw => text.includes(kw) && !text.includes("not good"))) {
      return { category: "Positive Feedback", subcategory: "", icon: "" };
    }
    
    // 4. General & Noise Check (Default Fallback)
    return { category: "General & Noise", subcategory: "General Inquiries", icon: "" };
  };

  // Filter & Search files logic based on Selected Category and Subcategory
  const filteredFiles = audioFiles.filter(file => {
    // Basic search query matches filename or transcript text
    const matchesSearch = file.filename.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          (file.transcript?.text || "").toLowerCase().includes(searchQuery.toLowerCase());
    if (!matchesSearch) return false;
    
    const classification = getCallCategory(file);
    
    // Filter by Category
    if (selectedCategory !== "All Categories" && classification.category !== selectedCategory) {
      return false;
    }
    
    // Filter by Subcategory
    if (selectedSubcategory !== "All" && classification.subcategory !== selectedSubcategory) {
      return false;
    }
    
    return true;
  });

  // Group files by date
  const groupedFilesByDate = filteredFiles.reduce((groups, file) => {
    const dateObj = new Date(file.created_at);
    const dateStr = dateObj.toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric"
    });
    if (!groups[dateStr]) {
      groups[dateStr] = [];
    }
    groups[dateStr].push(file);
    return groups;
  }, {} as Record<string, typeof filteredFiles>);

  const sortedDates = Object.keys(groupedFilesByDate).sort((a, b) => {
    return new Date(b).getTime() - new Date(a).getTime();
  });

  // Highlight searched word logic inside viewer segments
  const highlightText = (text: string, search: string) => {
    if (!search.trim()) return text;
    const regex = new RegExp(`(${escapeRegExp(search)})`, "gi");
    const parts = text.split(regex);
    return parts.map((part, index) => 
      regex.test(part) ? (
        <span key={index} className="search-highlight">{part}</span>
      ) : (
        part
      )
    );
  };

  const escapeRegExp = (str: string) => {
    return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  };

  return (
    <div className="flex h-screen bg-brand-bg text-white overflow-hidden">
      {/* Absolute Glow Background Elements */}
      <div className="absolute top-0 right-0 h-96 w-96 rounded-full bg-brand-green/5 blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-0 h-96 w-96 rounded-full bg-brand-green/5 blur-3xl pointer-events-none" />

      {/* Main Panel Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden relative z-10">
        
        {/* Top Header Bar */}
        <header className="h-16 border-b border-brand-border bg-brand-card px-8 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-4">
            {activeTab === "dashboard" ? (
              /* Brand Head Logo */
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-xl bg-brand-bg border border-brand-border flex items-center justify-center pulse-green-glow">
                  <BatteryCharging className="h-5.5 w-5.5 text-brand-green" />
                </div>
                <div className="leading-tight">
                  <h1 className="font-bold text-white tracking-wide text-sm">
                    OnePlug <span className="text-brand-green">EV</span>
                  </h1>
                  <span className="text-[9px] text-brand-text-muted font-mono uppercase tracking-widest block">
                    AI Speech Portal
                  </span>
                </div>
              </div>
            ) : (
              /* Back to Dashboard Button */
              <button
                onClick={() => {
                  setSelectedFile(null);
                  setAudioPreviewUrl(null);
                  setCustomPrompt("");
                  setActiveTab("dashboard");
                }}
                className="flex items-center gap-2 text-brand-text-muted hover:text-white transition font-medium text-xs cursor-pointer bg-brand-bg hover:bg-brand-border border border-brand-border rounded-lg px-3 py-1.5"
              >
                <ArrowLeft className="h-3.5 w-3.5" />
                Back to Dashboard
              </button>
            )}

            {/* Separator / Title info */}
            <div className="h-6 w-px bg-brand-border" />
            
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-brand-text-muted">
                {activeTab === "dashboard" && "EV Support Call Repository"}
                {activeTab === "upload" && "Ingest Call Audio"}
                {activeTab === "viewer" && "Interactive Transcript Analysis"}
              </h2>
              {activeTab === "viewer" && activeAudioFile && (
                <>
                  <ChevronRight className="h-4 w-4 text-brand-border" />
                  <span className="text-xs font-mono bg-brand-border/60 text-white px-2 py-0.5 rounded truncate max-w-xs">
                    {activeAudioFile.filename}
                  </span>
                </>
              )}
            </div>
          </div>
          
          <div className="flex items-center gap-4 text-xs">
            {activeTab === "dashboard" && (
              <>
                <div className="hidden lg:flex items-center gap-4 border-r border-brand-border pr-4 text-brand-text-muted font-mono text-xs">
                  <span>Calls: <span className="text-brand-green font-normal">{audioFiles.length}</span></span>
                  <span>Duration: <span className="text-brand-green font-normal">{formatTime(audioFiles.reduce((acc, curr) => acc + (curr.duration || 0), 0))}</span></span>
                  <span className="flex items-center gap-1.5">
                    Whisper API: <span className="h-2 w-2 rounded-full bg-brand-green animate-pulse"></span> <span className="text-brand-green font-normal">Active</span>
                  </span>
                </div>
                
                {/* Upload Button placed in Header */}
                <button
                  onClick={() => setActiveTab("upload")}
                  className="flex items-center gap-2 bg-brand-green text-brand-bg font-semibold text-xs px-3.5 py-1.5 rounded-lg hover:bg-brand-green-hover transition cursor-pointer"
                >
                  <UploadCloud className="h-4 w-4" />
                  Upload Call
                </button>
              </>
            )}

            {/* User Profile & Sign Out Controls */}
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-2 border border-brand-border bg-brand-bg/40 px-3 py-1.5 rounded-lg">
                <User className="h-3.5 w-3.5 text-brand-green" />
                <div className="text-left leading-none">
                  <p className="text-xs font-semibold text-white">{username}</p>
                  <p className="text-[9px] text-brand-text-muted">Agent #2026</p>
                </div>
              </div>
              <button
                onClick={handleLogout}
                title="Sign Out"
                className="p-2 rounded-lg border border-brand-border bg-brand-bg/40 text-brand-text-muted hover:bg-brand-border hover:text-red-400 transition cursor-pointer"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </header>

        {/* Tab Switcher Area */}
        <div className="flex-1 overflow-y-auto p-8">
          
          {/* TAB 1: CALL DASHBOARD OVERVIEW */}
          {activeTab === "dashboard" && (
            <div className="space-y-6 animate-fadeIn">
              
              {/* High-level Category Tabs */}
              <div className="flex border-b border-brand-border space-x-1 p-1 bg-brand-card/30 rounded-xl max-w-fit">
                {[
                  { name: "Support Issues", label: "Support Issues" },
                  { name: "Partnership Enquiries", label: "Partnership Enquiries" },
                  { name: "Positive Feedback", label: "Positive Feedback" },
                  { name: "General & Noise", label: "General & Noise" },
                  { name: "All Categories", label: "All Calls" }
                ].map((tab) => (
                  <button
                    key={tab.name}
                    onClick={() => {
                      setSelectedCategory(tab.name);
                      setSelectedSubcategory("All");
                    }}
                    className={`px-4 py-2.5 rounded-lg text-xs font-semibold tracking-wide transition cursor-pointer ${
                      selectedCategory === tab.name
                        ? "bg-brand-green/20 text-brand-green ring-1 ring-brand-green/30"
                        : "text-brand-text-muted hover:text-white hover:bg-brand-bg/40"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Sub-category Pill Selector */}
              {selectedCategory !== "All Categories" && selectedCategory === "General & Noise" && (
                <div className="flex flex-wrap items-center gap-2 pt-1 animate-fadeIn">
                  <span className="text-[10px] uppercase font-bold text-brand-text-muted tracking-wider mr-1">Subcategory:</span>
                  {(() => {
                    let subs: string[] = [];
                    if (selectedCategory === "General & Noise") {
                      subs = ["General Inquiries", "Junk / Hang-ups"];
                    }
                    return (
                      <>
                        <button
                          onClick={() => setSelectedSubcategory("All")}
                          className={`px-3 py-1 rounded-full text-xs font-medium transition cursor-pointer ${
                            selectedSubcategory === "All"
                              ? "bg-brand-green text-brand-bg font-semibold"
                              : "bg-brand-card hover:bg-brand-border text-brand-text-muted hover:text-white border border-brand-border"
                          }`}
                        >
                          All Subcategories
                        </button>
                        {subs.map((sub) => (
                          <button
                            key={sub}
                            onClick={() => setSelectedSubcategory(sub)}
                            className={`px-3 py-1 rounded-full text-xs font-medium transition cursor-pointer ${
                              selectedSubcategory === sub
                                ? "bg-brand-green text-brand-bg font-semibold"
                                : "bg-brand-card hover:bg-brand-border text-brand-text-muted hover:text-white border border-brand-border"
                            }`}
                          >
                            {sub}
                          </button>
                        ))}
                      </>
                    );
                  })()}
                </div>
              )}

              {/* Repository Table List Container */}
              <div className="bg-brand-card border border-brand-border rounded-xl overflow-hidden shadow-xl">
                
                {/* Table Header Filtering / Search Controls */}
                <div className="p-6 border-b border-brand-border flex flex-col md:flex-row md:items-center justify-between gap-4 bg-brand-card/55">
                  <div>
                    <h3 className="text-base font-bold text-white">Ingested Support Calls</h3>
                    <p className="text-xs text-brand-text-muted mt-1">Review, play and read call transcripts processed by OpenAI Whisper</p>
                  </div>
                  
                  <div className="flex flex-wrap items-center gap-3">
                    {/* Search Field */}
                    <div className="relative">
                      <Search className="absolute left-3 top-2.5 h-4 w-4 text-brand-text-muted" />
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search audio calls..."
                        className="bg-brand-bg text-xs text-white pl-9 pr-4 py-2.5 rounded-lg border border-brand-border focus:border-brand-green focus:outline-none w-56 transition placeholder-brand-text-muted/40"
                      />
                    </div>
                    
                    {/* Sync Refresh Button */}
                    <button
                      onClick={fetchAudioFiles}
                      className="bg-brand-bg hover:bg-brand-border border border-brand-border p-2.5 rounded-lg text-white transition flex items-center justify-center cursor-pointer"
                      title="Sync Repository"
                    >
                      <Loader2 className={`h-4 w-4 ${loadingList ? 'animate-spin text-brand-green' : ''}`} />
                    </button>
                  </div>
                </div>

                {/* Table Content */}
                <div className="overflow-x-auto">
                  {loadingList && audioFiles.length === 0 ? (
                    <div className="py-20 flex flex-col items-center justify-center space-y-3">
                      <Loader2 className="h-10 w-10 animate-spin text-brand-green" />
                      <p className="text-sm text-brand-text-muted">Syncing database calls...</p>
                    </div>
                  ) : filteredFiles.length === 0 ? (
                    <div className="py-20 text-center">
                      <FileAudio className="h-14 w-14 text-brand-border mx-auto mb-4" />
                      <p className="text-base font-semibold text-brand-text-muted">No Ingested Calls Found</p>
                      <p className="text-xs text-brand-text-muted mt-1 max-w-sm mx-auto">
                        There are no calls matching your filter. Upload call audio in the &apos;Upload Customer Call&apos; page to get started.
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-6 max-h-[calc(100vh-280px)] overflow-y-auto">
                      {sortedDates.map((dateStr) => {
                        const files = groupedFilesByDate[dateStr];
                        const sortedFiles = [...files].sort(
                          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
                        );
                        return (
                          <div key={dateStr} className="border border-brand-border/40 rounded-xl overflow-hidden bg-brand-card/25 shadow-lg">
                            {/* Date Group Header */}
                            <div 
                              onClick={() => toggleDateGroup(dateStr)}
                              className="bg-brand-bg/40 px-6 py-4 border-b border-brand-border/40 flex justify-between items-center bg-brand-card/20 cursor-pointer hover:bg-brand-card-hover/20 transition-all select-none"
                            >
                              <div className="flex items-center gap-2">
                                {expandedDates[dateStr] !== false ? (
                                  <ChevronDown className="h-4.5 w-4.5 text-brand-green" />
                                ) : (
                                  <ChevronRight className="h-4.5 w-4.5 text-brand-text-muted" />
                                )}
                                <h4 className="font-bold text-white text-base tracking-wide">{dateStr}</h4>
                              </div>
                              <span className="text-xs bg-brand-green/10 text-brand-green font-semibold px-2.5 py-1 rounded-full ring-1 ring-brand-green/20">
                                {sortedFiles.length} {sortedFiles.length === 1 ? "Recording" : "Recordings"}
                              </span>
                            </div>

                            {expandedDates[dateStr] !== false && (
                              <div className="overflow-x-auto">
                                <table className="w-full text-left border-collapse">
                                  <thead>
                                    <tr className="bg-brand-bg/25 text-brand-text-muted text-[10px] uppercase tracking-wider font-semibold border-b border-brand-border/20">
                                      <th className="py-3 px-6 w-[35%]">Filename</th>
                                      <th className="py-3 px-6">Time</th>
                                      <th className="py-3 px-6">File Size</th>
                                      <th className="py-3 px-6">Duration</th>
                                      <th className="py-3 px-6">Transcription Status</th>
                                      <th className="py-3 px-6 text-right">Actions</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-brand-border/20 text-sm">
                                    {sortedFiles.map((file, fileIndex) => {
                                      const lang = file.transcript?.language || "-";
                                      return (
                                        <tr
                                          key={file.id}
                                          onClick={() => file.status === "completed" && loadTranscriptDetails(file.id)}
                                          className={`hover:bg-brand-card-hover/40 transition-colors cursor-pointer ${
                                            file.status !== "completed" ? "opacity-75 pointer-events-none" : ""
                                          }`}
                                        >
                                          <td className="py-4 px-6 text-white truncate max-w-xs">
                                            <div className="flex items-center gap-3">
                                              <FileAudio className={`h-5 w-5 shrink-0 ${
                                                file.status === "completed" ? "text-brand-green" : "text-brand-text-muted"
                                              }`} />
                                              <div className="truncate flex flex-col">
                                                <span className="truncate">Call {sortedFiles.length - fileIndex}</span>

                                              </div>
                                            </div>
                                          </td>
                                          <td className="py-4 px-6 text-xs text-brand-text-muted font-mono">
                                            {new Date(file.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                          </td>
                                          <td className="py-4 px-6 text-xs text-brand-text-muted font-mono">
                                            {formatBytes(file.file_size)}
                                          </td>
                                          <td className="py-4 px-6 text-xs text-brand-text-muted font-mono">
                                            {file.duration ? formatTime(file.duration) : "Pending"}
                                          </td>
                                          <td className="py-4 px-6">
                                            <div className="flex items-center gap-2">
                                              {file.status === "pending" && (
                                                <span className="inline-flex items-center gap-1.5 rounded-full bg-yellow-400/10 px-2.5 py-0.5 text-xs font-medium text-yellow-300">
                                                  <Loader2 className="h-3 w-3 animate-spin" /> Pending Queued
                                                </span>
                                              )}
                                              {file.status === "processing" && (
                                                <span className="inline-flex items-center gap-1.5 rounded-full bg-cyan-400/10 px-2.5 py-0.5 text-xs font-medium text-cyan-300">
                                                  <Loader2 className="h-3 w-3 animate-spin" /> Transcribing...
                                                </span>
                                              )}
                                              {file.status === "completed" && (
                                                <span className="inline-flex items-center gap-1.5 rounded-full bg-brand-green/10 px-2.5 py-0.5 text-xs font-medium text-brand-green">
                                                  <CheckCircle2 className="h-3 w-3" /> Transcribed
                                                </span>
                                              )}
                                              {file.status === "failed" && (
                                                <span className="inline-flex items-center gap-1.5 rounded-full bg-red-400/10 px-2.5 py-0.5 text-xs font-medium text-red-300" title={file.error_message}>
                                                  <AlertTriangle className="h-3 w-3" /> Failed
                                                </span>
                                              )}
                                            </div>
                                          </td>
                                          <td className="py-4 px-6 text-right" onClick={(e) => e.stopPropagation()}>
                                            <div className="flex items-center justify-end gap-2">
                                              {file.status === "completed" && (
                                                <button
                                                  onClick={() => loadTranscriptDetails(file.id)}
                                                  className="text-xs bg-brand-border hover:bg-brand-green hover:text-brand-bg font-semibold text-white px-3 py-1.5 rounded-md transition cursor-pointer"
                                                >
                                                  Analyze Transcript
                                                </button>
                                              )}
                                              <button
                                                onClick={(e) => handleDeleteTranscript(e, file.id)}
                                                className="p-1.5 bg-brand-border/30 hover:bg-red-950/40 text-brand-text-muted hover:text-red-400 border border-brand-border/60 rounded-md transition cursor-pointer"
                                                title="Delete Recording"
                                              >
                                                <Trash2 className="h-3.5 w-3.5" />
                                              </button>
                                            </div>
                                          </td>
                                        </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: UPLOAD AUDIO CALL FOR WHISPER PROCESSING */}
          {activeTab === "upload" && (
            <div className="max-w-3xl mx-auto animate-fadeIn">
              <div className="bg-brand-card border border-brand-border rounded-xl p-8 shadow-xl">
                
                {/* Title */}
                <div className="mb-8 border-b border-brand-border pb-6">
                  <h3 className="text-xl font-bold text-white flex items-center gap-2">
                    <UploadCloud className="h-6 w-6 text-brand-green" /> Ingest Customer Call Recording
                  </h3>

                </div>

                {uploadError && (
                  <div className="mb-6 rounded-lg bg-red-900/20 border border-red-500/30 p-4 text-sm text-red-200 flex items-start gap-3">
                    <AlertTriangle className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
                    <span>{uploadError}</span>
                  </div>
                )}

                {uploadSuccess && (
                  <div className="mb-6 rounded-lg bg-brand-green/10 border border-brand-green/30 p-4 text-sm text-brand-green flex items-start gap-3">
                    <CheckCircle2 className="h-5 w-5 text-brand-green shrink-0 mt-0.5" />
                    <span>Call accepted successfully! Audio is queued for Whisper processing. Redirecting to Call Dashboard...</span>
                  </div>
                )}

                <form onSubmit={handleUploadSubmit} className="space-y-8">
                  {/* Drag and Drop Zone */}
                  <div>
                    <label className="block text-xs font-semibold text-brand-text-muted uppercase tracking-wider mb-3">
                      Audio Recording File
                    </label>
                    <div
                      onDragEnter={handleDrag}
                      onDragOver={handleDrag}
                      onDragLeave={handleDrag}
                      onDrop={handleDrop}
                      className={`relative border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center transition ${
                        dragActive 
                          ? "border-brand-green bg-brand-green/5" 
                          : selectedFile 
                          ? "border-brand-green/45 bg-brand-card/85" 
                          : "border-brand-border hover:border-brand-green/50 bg-brand-bg/50"
                      }`}
                    >
                      <input
                        type="file"
                        id="audio-upload"
                        accept=".mp3,.wav,.m4a,.ogg,.flac"
                        onChange={handleFileChange}
                        disabled={isUploading}
                        className="hidden"
                      />
                      
                      {!selectedFile ? (
                        <div className="text-center space-y-3">
                          <div className="h-12 w-12 rounded-full bg-brand-bg border border-brand-border flex items-center justify-center mx-auto text-brand-text-muted">
                            <UploadCloud className="h-6 w-6" />
                          </div>
                          <div>
                            <p className="text-sm font-semibold text-white">
                              Drag & drop call audio here, or{" "}
                              <label htmlFor="audio-upload" className="text-brand-green hover:underline cursor-pointer">
                                browse local files
                              </label>
                            </p>
                            <p className="text-xs text-brand-text-muted mt-1">
                              Supports MP3, WAV, M4A up to 25MB
                            </p>
                          </div>
                        </div>
                      ) : (
                        <div className="w-full flex flex-col items-center space-y-4">
                          <div className="flex items-center gap-3 bg-brand-bg border border-brand-border rounded-lg p-3 w-full max-w-md">
                            <FileAudio className="h-8 w-8 text-brand-green shrink-0" />
                            <div className="truncate flex-1">
                              <p className="text-sm font-semibold text-white truncate">{selectedFile.name}</p>
                              <p className="text-xs text-brand-text-muted font-mono">{formatBytes(selectedFile.size)}</p>
                            </div>
                            <button
                              type="button"
                              onClick={() => {
                                setSelectedFile(null);
                                setAudioPreviewUrl(null);
                              }}
                              disabled={isUploading}
                              className="text-xs font-semibold text-brand-text-muted hover:text-red-400 px-2 py-1 transition cursor-pointer"
                            >
                              Reset
                            </button>
                          </div>

                          {/* Pre-upload Audio Preview player */}
                          {audioPreviewUrl && (
                            <div className="w-full max-w-md bg-brand-bg border border-brand-border rounded-lg p-3">
                              <p className="text-[11px] font-semibold text-brand-green uppercase tracking-wider mb-2">
                                Pre-upload Audio Player
                              </p>
                              <audio
                                src={audioPreviewUrl}
                                controls
                                className="w-full h-8 accent-brand-green"
                              />
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>



                  {/* Active Upload/Transcription Progress indicator */}
                  {isUploading && (
                    <div className="space-y-3 bg-brand-bg/60 border border-brand-border rounded-xl p-5">
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-brand-green font-semibold flex items-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin text-brand-green" />
                          {uploadStage}
                        </span>
                        <span className="font-mono text-white font-bold">{uploadProgress}%</span>
                      </div>
                      
                      {/* Custom styled HTML progress bar */}
                      <div className="w-full bg-brand-border rounded-full h-2">
                        <div
                          className="bg-brand-green h-2 rounded-full transition-all duration-300 shadow-[0_0_8px_rgba(0,230,118,0.5)]"
                          style={{ width: `${uploadProgress}%` }}
                        ></div>
                      </div>
                    </div>
                  )}

                  {/* Form Submission Button */}
                  <div className="flex justify-end gap-3 border-t border-brand-border pt-6">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedFile(null);
                        setAudioPreviewUrl(null);
                        setCustomPrompt("");
                        setActiveTab("dashboard");
                      }}
                      disabled={isUploading}
                      className="px-5 py-3 rounded-lg text-sm font-semibold text-brand-text-muted hover:text-white transition bg-brand-border/30 hover:bg-brand-border/60 cursor-pointer"
                    >
                      Cancel
                    </button>
                    
                    <button
                      type="submit"
                      disabled={!selectedFile || isUploading}
                      className="group relative flex justify-center items-center gap-2 rounded-lg bg-brand-green px-6 py-3 text-sm font-semibold text-brand-bg hover:bg-brand-green-hover focus-visible:outline transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
                    >
                      {isUploading ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin text-brand-bg" />
                          Processing...
                        </>
                      ) : (
                        "Upload & Transcribe Call"
                      )}
                    </button>
                  </div>

                </form>

              </div>
            </div>
          )}

          {/* TAB 3: TRANSCRIPT VIEWER PAGE */}
          {activeTab === "viewer" && (
            <div className="h-full animate-fadeIn">
              
              {!activeAudioFile ? (
                /* Empty Viewer State Card */
                <div className="max-w-2xl mx-auto text-center py-24 bg-brand-card border border-brand-border rounded-xl p-8 shadow-xl">
                  <div className="h-16 w-16 rounded-full bg-brand-bg border border-brand-border flex items-center justify-center mx-auto text-brand-text-muted mb-4 pulse-green-glow">
                    <FileText className="h-8 w-8 text-brand-green" />
                  </div>
                  <h3 className="text-lg font-bold text-white">No Active Transcript Selected</h3>
                  <p className="text-xs text-brand-text-muted mt-2 max-w-sm mx-auto">
                    Select an ingested call from the Call Dashboard to view its transcripts, search terms, and download reports. Or click below to ingest a new audio log.
                  </p>
                  <button
                    onClick={() => setActiveTab("upload")}
                    className="mt-6 inline-flex items-center gap-2 bg-brand-green text-brand-bg font-semibold text-xs px-4 py-2.5 rounded-lg hover:bg-brand-green-hover transition cursor-pointer"
                  >
                    <UploadCloud className="h-4 w-4" /> Ingest Call Audio
                  </button>
                </div>
              ) : (
                /* Dynamic Transcript Viewer Interface */
                <div className="flex flex-col gap-6 animate-fadeIn">
                                   {/* HEADER SECTION: COMPACT AUDIO & CONTROL BAR */}
                  <div className="bg-brand-card border border-brand-border rounded-xl p-4 shadow-xl flex flex-col md:flex-row items-center justify-between gap-4">
                    {/* Left: Filename & Duration */}
                    <div className="flex flex-col md:flex-row items-baseline gap-2 md:gap-4 w-full md:w-auto shrink-0">
                      <h3 className="font-bold text-white text-base truncate max-w-xs md:max-w-md">
                        {(() => { const dateKey = new Date(activeAudioFile.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" }); const dayFiles = [...(groupedFilesByDate[dateKey] || [])].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()); const idx = dayFiles.findIndex(f => f.id === activeAudioFile.id); return `Call ${idx + 1}`; })()}
                      </h3>
                      <span className="text-sm text-brand-text-muted font-mono whitespace-nowrap">
                        Duration: <span className="text-white font-semibold">{formatTime(activeAudioFile.duration || 0)}</span>
                      </span>
                    </div>

                    {/* Middle: Audio Player */}
                    <div className="flex-1 w-full max-w-lg md:mx-4">
                      <audio
                        ref={audioPlayerRef}
                        src={audioStreamUrl || undefined}
                        className="w-full h-8 accent-brand-green bg-brand-bg rounded-lg"
                        controls
                        onPlay={() => setIsPlaying(true)}
                        onPause={() => setIsPlaying(false)}
                        onTimeUpdate={(e) => {
                          if (audioPlayerRef.current) {
                            setCurrentTime(audioPlayerRef.current.currentTime);
                          }
                        }}
                      />
                    </div>

                    {/* Right: Speed + Download Options */}
                    <div className="flex items-center gap-4 shrink-0 flex-wrap">
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs text-brand-text-muted font-semibold uppercase tracking-wider">Speed:</span>
                        {[1, 1.25, 1.5, 1.75, 2].map(speed => (
                          <button
                            key={speed}
                            onClick={() => {
                              setPlaybackSpeed(speed);
                              if (audioPlayerRef.current) audioPlayerRef.current.playbackRate = speed;
                            }}
                            className={`px-2 py-1 rounded text-xs font-semibold transition cursor-pointer ${playbackSpeed === speed ? "bg-brand-green text-brand-bg" : "bg-brand-card text-brand-text-muted hover:text-white border border-brand-border"}`}
                          >
                            {speed}x
                          </button>
                        ))}
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-xs text-brand-text-muted font-semibold uppercase tracking-wider">Download:</span>
                        <button
                          onClick={downloadText}
                          className="text-xs bg-brand-bg hover:bg-brand-border hover:text-brand-green text-white border border-brand-border px-3 py-1.5 rounded font-semibold transition cursor-pointer"
                        >
                          TXT
                        </button>
                        {audioStreamUrl && (
                          
                          <a
                            href={audioStreamUrl}
                            download
                            className="text-xs bg-brand-bg hover:bg-brand-border hover:text-brand-green text-white border border-brand-border px-3 py-1.5 rounded font-semibold transition cursor-pointer"
                          >
                            MP3
                          </a>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* BOTTOM SECTION: SIDE-BY-SIDE 50/50 SPLIT */}
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
                    
                    {/* LEFT COLUMN: AI EXPLANATION & CALL TRANSCRIPT (col-span-6) */}
                    <div className="lg:col-span-6 flex flex-col gap-6">
                      {/* What Happened narrative box */}
                      {activeAudioFile.transcript?.analysis?.analysed && (
                        <div className="bg-brand-card border border-brand-border rounded-xl p-6 shadow-xl space-y-4">
                          <h4 className="text-sm font-semibold text-brand-text-muted uppercase tracking-wider flex items-center gap-1.5 border-b border-brand-border/40 pb-3">
                            <Brain className="h-3.5 w-3.5 text-brand-green animate-pulse" /> What Happened (AI Explanation)
                          </h4>
                          <p className="text-sm sm:text-base text-brand-text/95 leading-relaxed font-sans text-slate-100">
                            {activeAudioFile.transcript.analysis.what_happened || "This call was transcribed before the AI Explanation feature was added. Please upload a new call to view the detailed chronological narrative."}
                          </p>
                        </div>
                      )}

                      {/* Call Transcript box */}
                      <div className="bg-brand-card border border-brand-border rounded-xl flex-1 flex flex-col overflow-hidden shadow-xl" style={{ minHeight: "450px", maxHeight: "calc(100vh - 350px)" }}>
                        {/* Dialogue Script Head */}
                        <div className="p-5 border-b border-brand-border bg-brand-card/55 flex justify-between items-center shrink-0">
                          <div>
                            <h4 className="text-base font-bold text-white">Call Transcript</h4>
                            <p className="text-sm text-brand-text-muted mt-0.5">Click any sentence to jump the audio player to that point</p>
                          </div>
                        </div>

                        {/* Dialogue turns list container */}
                        <div className="flex-1 overflow-y-auto p-6 space-y-4">
                          {loadingDetail ? (
                            <div className="h-full flex flex-col items-center justify-center space-y-3">
                              <Loader2 className="h-8 w-8 animate-spin text-brand-green" />
                              <p className="text-sm text-brand-text-muted">Loading speech segments...</p>
                            </div>
                          ) : !activeAudioFile.transcript?.segments || activeAudioFile.transcript.segments.length === 0 ? (
                            /* ── NO SEGMENTS ──────────────────────────────── */
                            <div className="text-base leading-relaxed text-brand-text whitespace-pre-wrap">
                              {activeAudioFile.transcript?.text || "No transcript text available."}
                            </div>
                          ) : (
                            /* ── TRANSCRIPT (Unified Text Layout) ──────────────────────── */
                            <div className="text-base leading-relaxed text-brand-text/90 font-sans">
                              <div className="flex flex-wrap items-baseline gap-y-2">
                                {activeAudioFile.transcript.segments.map((seg) => {
                                  const isActive = currentTime >= seg.start && currentTime <= seg.end;
                                  return (
                                    <span
                                      key={seg.id}
                                      onClick={() => handleJumpToTime(seg.start)}
                                      className={`inline cursor-pointer transition-all duration-150 px-1 py-0.5 rounded mr-1.5 ${
                                        isActive
                                          ? "bg-brand-green/20 text-brand-green border border-brand-green/30 shadow-[0_0_8px_rgba(0,230,118,0.15)] font-medium"
                                          : "hover:bg-brand-border/40 hover:text-white"
                                      }`}
                                      title={`Click to jump to ${formatTime(seg.start)}`}
                                    >
                                      {seg.text}
                                    </span>
                                  );
                                })}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* RIGHT COLUMN: AI SUMMARY & CALL ANALYSIS (col-span-6) */}
                    <div className="lg:col-span-6 flex flex-col gap-6">
                      {activeAudioFile.transcript?.analysis?.analysed && (() => {
                        const a = activeAudioFile.transcript!.analysis!;
                        const severityColor =
                          a.severity === "High"
                            ? "text-red-400 bg-red-400/10 ring-red-400/20"
                            : a.severity === "Medium"
                            ? "text-amber-400 bg-amber-400/10 ring-amber-400/20"
                            : "text-brand-green bg-brand-green/10 ring-brand-green/20";
                        const sentimentColor =
                          a.sentiment === "Positive"
                            ? "text-brand-green bg-brand-green/10 ring-brand-green/20"
                            : a.sentiment === "Negative"
                            ? "text-red-400 bg-red-400/10 ring-red-400/20"
                            : "text-slate-300 bg-slate-400/10 ring-slate-400/20";
                        const SentimentIcon =
                          a.sentiment === "Positive" ? ThumbsUp
                          : a.sentiment === "Negative" ? ThumbsDown
                          : Minus;

                        return (
                          <>
                            {/* Summary Card */}
                            <div className="bg-brand-card border border-brand-border rounded-xl p-6 shadow-xl space-y-4">
                              <h4 className="text-sm font-semibold text-brand-text-muted uppercase tracking-wider flex items-center gap-1.5 border-b border-brand-border/40 pb-3">
                                <MessageSquare className="h-3.5 w-3.5 text-brand-green" /> AI Call Summary
                              </h4>
                              <p className="text-sm sm:text-base text-brand-text leading-relaxed font-sans text-slate-100">
                                {a.summary}
                              </p>
                            </div>

                            {/* Analysis Card */}
                            <div className="bg-brand-card border border-brand-border rounded-xl p-6 shadow-xl space-y-5">
                              <div className="space-y-5">
                                {/* Panel header */}
                                <h4 className="text-sm font-semibold text-brand-text-muted uppercase tracking-wider flex items-center gap-1.5 border-b border-brand-border/40 pb-3">
                                  <Brain className="h-3.5 w-3.5 text-brand-green" /> AI Call Analysis
                                </h4>

                                {/* Badges row */}
                                <div className="flex flex-wrap gap-2">
                                  {/* Sentiment badge */}
                                  <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold ring-1 ${sentimentColor}`}>
                                    <SentimentIcon className="h-3 w-3" />
                                    {a.sentiment}
                                  </span>

                                  {/* Issue badge */}
                                  {a.issue_detected && a.issue_type && (
                                    <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-semibold text-amber-300 bg-amber-400/10 ring-1 ring-amber-400/20">
                                      <ShieldAlert className="h-3 w-3" />
                                      {a.issue_type}
                                    </span>
                                  )}

                                  {/* Severity badge */}
                                  {a.severity && (
                                    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-bold ring-1 ${severityColor}`}>
                                      <Zap className="h-3 w-3" />
                                      {a.severity} Severity
                                    </span>
                                  )}
                                </div>

                                {/* Issue alert block */}
                                {a.issue_detected && (
                                  <div className="rounded-lg bg-amber-400/10 border border-amber-400/30 p-4 space-y-2">
                                    <p className="text-sm font-bold text-amber-400 uppercase tracking-wider">Issue Flagged</p>
                                    <p className="text-base sm:text-lg text-white font-bold">{a.issue_type}</p>
                                    {a.all_issues.length > 1 && (
                                      <div className="flex flex-wrap gap-1 mt-1">
                                        {a.all_issues.slice(1).map((iss, idx) => (
                                          <span key={idx} className="text-xs text-brand-text-muted bg-brand-border/40 rounded px-1.5 py-0.5">
                                            +{iss.issue_type}
                                          </span>
                                        ))}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>

                              {/* Structured fields */}
                              <div className="space-y-3 border-t border-brand-border/40 pt-4 mt-4">
                                {/* Main Concern */}
                                <div className="flex flex-col gap-1 p-3 rounded-lg bg-red-500/5 border border-red-500/10 border-l-4 border-l-red-500/60">
                                  <span className="text-xs font-bold text-red-400 uppercase tracking-wider">Main Concern</span>
                                  <span className="text-sm sm:text-base text-white leading-relaxed">{a.main_concern}</span>
                                </div>
                                {/* Outcome */}
                                <div className="flex flex-col gap-1 p-3 rounded-lg bg-emerald-500/5 border border-emerald-500/10 border-l-4 border-l-brand-green/60">
                                  <span className="text-xs font-bold text-brand-green uppercase tracking-wider">Outcome</span>
                                  <span className="text-sm sm:text-base text-white leading-relaxed">{a.outcome}</span>
                                </div>
                                {/* Action Needed */}
                                <div className="flex flex-col gap-1 p-3 rounded-lg bg-amber-500/5 border border-amber-500/10 border-l-4 border-l-amber-500/60">
                                  <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">Action Needed</span>
                                  <span className="text-sm sm:text-base text-white leading-relaxed">{a.action_needed}</span>
                                </div>
                              </div>
                            </div>
                          </>
                        );
                      })()}
                    </div>
                  </div>
                </div>
              )
            }
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
