"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";

// API base URL for the ML service
const ML_SERVICE_URL = process.env.NEXT_PUBLIC_ML_SERVICE_URL || "http://localhost:8000";

type JobStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

interface JobProgress {
  current_step: string | null;
  steps_completed: string[];
  total_chunks: number | null;
  total_pages: number | null;
}

interface JobResponse {
  job_id: string;
  status: JobStatus;
  filename: string;
  created_at: string;
  updated_at: string;
  progress: JobProgress;
  error_message: string | null;
}

interface ExtractedData {
  title: string | null;
  author: string | null;
  summary: string | null;
  document_type: string | null;
  key_topics: string[] | null;
}

const STEPS = ["parsing", "extracting", "chunking", "embedding", "completed"];

function StepIndicator({ currentStep, status }: { currentStep: string | null; status: JobStatus }) {
  const getStepStatus = (step: string): "completed" | "current" | "pending" | "error" => {
    if (status === "FAILED") return "error";
    if (status === "COMPLETED") return "completed";
    if (!currentStep) return "pending";
    
    const currentIdx = STEPS.indexOf(currentStep);
    const stepIdx = STEPS.indexOf(step);
    
    if (stepIdx < currentIdx) return "completed";
    if (stepIdx === currentIdx) return "current";
    return "pending";
  };

  return (
    <div className="flex items-center justify-between w-full max-w-2xl mx-auto my-8">
      {STEPS.slice(0, -1).map((step, idx) => {
        const stepStatus = getStepStatus(step);
        return (
          <div key={step} className="flex items-center flex-1">
            <div className="flex flex-col items-center">
              <div
                className={`
                  w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm transition-all duration-300
                  ${stepStatus === "completed" ? "bg-emerald-500 text-white" : ""}
                  ${stepStatus === "current" ? "bg-amber-500 text-white animate-pulse" : ""}
                  ${stepStatus === "pending" ? "bg-zinc-700 text-zinc-400" : ""}
                  ${stepStatus === "error" ? "bg-red-500 text-white" : ""}
                `}
              >
                {stepStatus === "completed" ? "✓" : idx + 1}
              </div>
              <span className="mt-2 text-xs text-zinc-400 capitalize">{step}</span>
            </div>
            {idx < STEPS.length - 2 && (
              <div
                className={`
                  flex-1 h-1 mx-2 rounded transition-all duration-300
                  ${getStepStatus(STEPS[idx + 1]) !== "pending" ? "bg-emerald-500" : "bg-zinc-700"}
                `}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

function FileUploadZone({
  onFileSelect,
  isUploading,
  selectedFile,
}: {
  onFileSelect: (file: File) => void;
  isUploading: boolean;
  selectedFile: File | null;
}) {
  const [isDragging, setIsDragging] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDragIn = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  };

  const handleDragOut = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type === "application/pdf") {
        onFileSelect(file);
      }
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      onFileSelect(files[0]);
    }
  };

  return (
    <div
      onDragEnter={handleDragIn}
      onDragLeave={handleDragOut}
      onDragOver={handleDrag}
      onDrop={handleDrop}
      className={`
        relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 cursor-pointer
        ${isDragging ? "border-amber-500 bg-amber-500/10" : "border-zinc-600 hover:border-zinc-500"}
        ${isUploading ? "opacity-50 pointer-events-none" : ""}
      `}
    >
      <input
        type="file"
        accept=".pdf"
        onChange={handleFileInput}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        disabled={isUploading}
      />
      
      <div className="text-6xl mb-4">📄</div>
      
      {selectedFile ? (
        <div>
          <p className="text-lg font-medium text-white">{selectedFile.name}</p>
          <p className="text-sm text-zinc-400 mt-1">
            {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
          </p>
        </div>
      ) : (
        <div>
          <p className="text-lg text-zinc-300">
            Drop your PDF here or <span className="text-amber-500 underline">browse</span>
          </p>
          <p className="text-sm text-zinc-500 mt-2">Maximum file size: 50MB</p>
        </div>
      )}
    </div>
  );
}

function ResultsCard({ job, extractedData }: { job: JobResponse; extractedData: ExtractedData | null }) {
  return (
    <div className="bg-zinc-800/50 rounded-2xl p-6 border border-zinc-700">
      <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
        <span className="text-2xl">✅</span> Ingestion Complete
      </h3>
      
      <div className="grid gap-4">
        <div className="bg-zinc-900/50 rounded-xl p-4">
          <h4 className="text-sm text-zinc-400 mb-1">Document</h4>
          <p className="text-white font-medium">{job.filename}</p>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-zinc-900/50 rounded-xl p-4">
            <h4 className="text-sm text-zinc-400 mb-1">Pages</h4>
            <p className="text-2xl font-bold text-amber-500">{job.progress.total_pages || "—"}</p>
          </div>
          <div className="bg-zinc-900/50 rounded-xl p-4">
            <h4 className="text-sm text-zinc-400 mb-1">Chunks</h4>
            <p className="text-2xl font-bold text-emerald-500">{job.progress.total_chunks || "—"}</p>
          </div>
        </div>
        
        {extractedData && (
          <>
            {extractedData.title && (
              <div className="bg-zinc-900/50 rounded-xl p-4">
                <h4 className="text-sm text-zinc-400 mb-1">Extracted Title</h4>
                <p className="text-white">{extractedData.title}</p>
              </div>
            )}
            
            {extractedData.summary && (
              <div className="bg-zinc-900/50 rounded-xl p-4">
                <h4 className="text-sm text-zinc-400 mb-1">Summary</h4>
                <p className="text-white text-sm">{extractedData.summary}</p>
              </div>
            )}
            
            {extractedData.key_topics && extractedData.key_topics.length > 0 && (
              <div className="bg-zinc-900/50 rounded-xl p-4">
                <h4 className="text-sm text-zinc-400 mb-2">Key Topics</h4>
                <div className="flex flex-wrap gap-2">
                  {extractedData.key_topics.map((topic, idx) => (
                    <span
                      key={idx}
                      className="px-3 py-1 bg-amber-500/20 text-amber-400 rounded-full text-sm"
                    >
                      {topic}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function IngestPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [currentJob, setCurrentJob] = useState<JobResponse | null>(null);
  const [extractedData, setExtractedData] = useState<ExtractedData | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Poll for job status
  const pollJobStatus = useCallback(async (jobId: string) => {
    try {
      const response = await fetch(`${ML_SERVICE_URL}/api/v1/jobs/${jobId}`);
      if (!response.ok) throw new Error("Failed to fetch job status");
      
      const job: JobResponse = await response.json();
      setCurrentJob(job);
      
      if (job.status === "COMPLETED") {
        // Fetch extracted data
        try {
          const extractedResponse = await fetch(
            `${ML_SERVICE_URL}/api/v1/jobs/${jobId}/extracted`
          );
          if (extractedResponse.ok) {
            const data = await extractedResponse.json();
            setExtractedData(data);
          }
        } catch (e) {
          console.error("Failed to fetch extracted data:", e);
        }
        return true; // Stop polling
      }
      
      if (job.status === "FAILED") {
        setError(job.error_message || "Ingestion failed");
        return true; // Stop polling
      }
      
      return false; // Continue polling
    } catch (e) {
      console.error("Polling error:", e);
      return false;
    }
  }, []);

  useEffect(() => {
    if (!currentJob || currentJob.status === "COMPLETED" || currentJob.status === "FAILED") {
      return;
    }

    const interval = setInterval(async () => {
      const shouldStop = await pollJobStatus(currentJob.job_id);
      if (shouldStop) {
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [currentJob, pollJobStatus]);

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setError(null);
    setCurrentJob(null);
    setExtractedData(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);

      const response = await fetch(`${ML_SERVICE_URL}/api/v1/ingest`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Upload failed");
      }

      const data = await response.json();
      setCurrentJob({
        job_id: data.job_id,
        status: data.status,
        filename: selectedFile.name,
        created_at: data.created_at,
        updated_at: data.created_at,
        progress: {
          current_step: null,
          steps_completed: [],
          total_chunks: null,
          total_pages: null,
        },
        error_message: null,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setCurrentJob(null);
    setExtractedData(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-zinc-900 text-white">
      {/* Header */}
      <header className="border-b border-zinc-800">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">
              <span className="text-amber-500">📚</span> Document Ingestion
            </h1>
            <p className="text-zinc-400 text-sm mt-1">
              Upload PDFs for AI-powered processing and vector storage
            </p>
          </div>
          <Link
            href="/documents"
            className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl transition-colors text-sm"
          >
            View Library →
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 py-8">
        {/* Error Alert */}
        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-400 px-4 py-3 rounded-xl mb-6 flex items-center gap-3">
            <span className="text-xl">⚠️</span>
            <div>
              <p className="font-medium">Ingestion Failed</p>
              <p className="text-sm opacity-80">{error}</p>
            </div>
            <button
              onClick={handleReset}
              className="ml-auto text-sm underline hover:no-underline"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Progress Indicator */}
        {currentJob && currentJob.status !== "FAILED" && (
          <StepIndicator
            currentStep={currentJob.progress.current_step}
            status={currentJob.status}
          />
        )}

        {/* Upload Zone or Results */}
        {currentJob?.status === "COMPLETED" ? (
          <div className="space-y-6">
            <ResultsCard job={currentJob} extractedData={extractedData} />
            <button
              onClick={handleReset}
              className="w-full py-4 bg-zinc-800 hover:bg-zinc-700 text-white rounded-xl font-medium transition-colors"
            >
              Upload Another Document
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            <FileUploadZone
              onFileSelect={setSelectedFile}
              isUploading={isUploading || (currentJob?.status === "PROCESSING" || currentJob?.status === "PENDING")}
              selectedFile={selectedFile}
            />

            {selectedFile && !currentJob && (
              <button
                onClick={handleUpload}
                disabled={isUploading}
                className={`
                  w-full py-4 rounded-xl font-bold text-lg transition-all duration-300
                  ${isUploading
                    ? "bg-zinc-700 text-zinc-400 cursor-not-allowed"
                    : "bg-amber-500 hover:bg-amber-400 text-zinc-900"
                  }
                `}
              >
                {isUploading ? "Uploading..." : "Start Ingestion"}
              </button>
            )}

            {currentJob && (currentJob.status === "PENDING" || currentJob.status === "PROCESSING") && (
              <div className="text-center py-8">
                <div className="inline-block animate-spin text-4xl mb-4">⚙️</div>
                <p className="text-lg text-zinc-300">
                  Processing <span className="font-medium text-white">{currentJob.filename}</span>
                </p>
                <p className="text-sm text-zinc-500 mt-2">
                  {currentJob.progress.current_step
                    ? `Current step: ${currentJob.progress.current_step}`
                    : "Initializing..."}
                </p>
              </div>
            )}
          </div>
        )}

        {/* Info Card */}
        <div className="mt-12 bg-zinc-800/30 rounded-2xl p-6 border border-zinc-800">
          <h3 className="text-lg font-bold text-white mb-3">How it works</h3>
          <div className="grid md:grid-cols-4 gap-4 text-sm">
            <div className="flex items-start gap-3">
              <span className="text-2xl">1️⃣</span>
              <div>
                <p className="font-medium text-white">Parse</p>
                <p className="text-zinc-400">Extract text from PDF</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">2️⃣</span>
              <div>
                <p className="font-medium text-white">Extract</p>
                <p className="text-zinc-400">AI extracts metadata</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">3️⃣</span>
              <div>
                <p className="font-medium text-white">Chunk</p>
                <p className="text-zinc-400">Split into segments</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <span className="text-2xl">4️⃣</span>
              <div>
                <p className="font-medium text-white">Embed</p>
                <p className="text-zinc-400">Generate vectors</p>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

