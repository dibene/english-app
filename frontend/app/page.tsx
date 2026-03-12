"use client";

import { useRef, useState } from "react";
import { analyze, AnalyzeResponse } from "../lib/api";

type RecorderStatus = "idle" | "recording" | "processing" | "done" | "error";

export default function Home() {
  const [sentence, setSentence] = useState("");
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  async function startRecording() {
    setResult(null);
    setErrorMsg(null);

    if (!navigator.mediaDevices?.getUserMedia) {
      setErrorMsg("Audio recording is not supported in this browser.");
      setStatus("error");
      return;
    }

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (err) {
      const name = err instanceof Error ? err.name : "";
      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        setErrorMsg("Microphone permission denied. Please allow access and try again.");
      } else {
        setErrorMsg("Could not access microphone. Make sure a mic is connected.");
      }
      setStatus("error");
      return;
    }

    chunksRef.current = [];
    const recorder = new MediaRecorder(stream);
    mediaRecorderRef.current = recorder;

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) chunksRef.current.push(e.data);
    };

    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      setStatus("processing");
      try {
        const data = await analyze(blob, sentence);
        setResult(data);
        setStatus("done");
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Unexpected error from backend.");
        setStatus("error");
      }
    };

    recorder.start();
    setStatus("recording");
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
  }

  const isRecording = status === "recording";
  const isProcessing = status === "processing";
  const canRecord = !isRecording && !isProcessing && sentence.trim().length > 0;

  return (
    <main className="max-w-2xl mx-auto p-8 space-y-6">
      <h1 className="text-2xl font-bold">Read &amp; Improve</h1>

      <div className="space-y-2">
        <label htmlFor="sentence" className="block font-medium">
          Sentence to pronounce
        </label>
        <textarea
          id="sentence"
          className="w-full border border-gray-300 rounded p-2 font-mono text-sm"
          rows={3}
          placeholder="Type a sentence here…"
          value={sentence}
          onChange={(e) => setSentence(e.target.value)}
          disabled={isRecording || isProcessing}
        />
      </div>

      <div className="flex items-center gap-4">
        {!isRecording ? (
          <button
            onClick={startRecording}
            disabled={!canRecord}
            className="px-4 py-2 bg-blue-600 text-white rounded disabled:opacity-40"
          >
            {isProcessing ? "Processing…" : "Record"}
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="px-4 py-2 bg-red-600 text-white rounded"
          >
            Stop
          </button>
        )}

        <span className="text-sm text-gray-500">
          {status === "idle" && "Enter a sentence, then record."}
          {status === "recording" && "Recording… press Stop when done."}
          {status === "processing" && "Sending to backend…"}
          {status === "done" && "Done!"}
          {status === "error" && "Something went wrong."}
        </span>
      </div>

      {errorMsg && (
        <div className="border border-red-300 bg-red-50 text-red-700 rounded p-3 text-sm">
          {errorMsg}
        </div>
      )}

      {result && (
        <div className="space-y-1">
          <p className="font-medium text-sm">Raw response:</p>
          <pre className="bg-gray-100 rounded p-3 text-xs overflow-auto">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </main>
  );
}
