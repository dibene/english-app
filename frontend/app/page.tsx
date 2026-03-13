"use client";

import { useEffect, useRef, useState } from "react";
import { analyze, AnalyzeResponse } from "../lib/api";
import SentenceList, { splitSentences } from "../components/SentenceList";
import BilingualSentenceList, { parseBilingualText } from "../components/BilingualSentenceList";
import FeedbackPanel from "../components/FeedbackPanel";

const MAX_CHARS = 500;

type RecorderStatus = "idle" | "recording" | "preview" | "processing" | "done" | "error";

export default function Home() {
  const [text, setText] = useState("");
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [mode, setMode] = useState<"free" | "bilingual">("free");
  const [bilingualText, setBilingualText] = useState("");
  const [selectedPairIdx, setSelectedPairIdx] = useState<number | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // revoke object URL on unmount
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  const sentences = splitSentences(text.trim());
  const freeSentence = selectedIdx !== null ? (sentences[selectedIdx] ?? null) : null;

  const pairs = parseBilingualText(bilingualText);
  const bilingualSentence = selectedPairIdx !== null ? (pairs[selectedPairIdx]?.english ?? null) : null;

  const selectedSentence = mode === "free" ? freeSentence : bilingualSentence;

  function resetToIdle() {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioBlob(null);
    setAudioUrl(null);
    setResult(null);
    setErrorMsg(null);
    setStatus("idle");
  }

  function switchMode(newMode: "free" | "bilingual") {
    setMode(newMode);
    setSelectedIdx(null);
    setSelectedPairIdx(null);
    resetToIdle();
  }

  async function startRecording() {
    resetToIdle();

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

    recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      const url = URL.createObjectURL(blob);
      setAudioBlob(blob);
      setAudioUrl(url);
      setStatus("preview");
    };

    recorder.start();
    setStatus("recording");
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
  }

  async function sendAudio() {
    if (!audioBlob || !selectedSentence) return;
    setStatus("processing");
    try {
      const data = await analyze(audioBlob, selectedSentence);
      setResult(data);
      setStatus("done");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Unexpected error from backend.");
      setStatus("error");
    }
  }

  const isRecording = status === "recording";
  const isProcessing = status === "processing";
  const isPreview = status === "preview";
  const canRecord =
    !isRecording && !isProcessing && !isPreview &&
    selectedSentence !== null &&
    (mode === "bilingual" || !overLimit);

  const charCount = text.length;
  const overLimit = charCount > MAX_CHARS;

  return (
    <main className="max-w-2xl mx-auto p-8 space-y-6">
      <h1 className="text-2xl font-bold">Read &amp; Improve</h1>

      {/* Mode tabs */}
      <div className="flex gap-1 rounded-lg bg-gray-100 p-1 w-fit">
        <button
          onClick={() => switchMode("free")}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${mode === "free" ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"
            }`}
        >
          Free Text
        </button>
        <button
          onClick={() => switchMode("bilingual")}
          className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${mode === "bilingual" ? "bg-white shadow text-gray-900" : "text-gray-500 hover:text-gray-700"
            }`}
        >
          ES → EN Sentences
        </button>
      </div>

      {/* Free Text mode */}
      {mode === "free" && (
        <>
          {/* textarea + char counter */}
          <div className="space-y-1">
            <label htmlFor="text-input" className="block font-medium">
              Text to practise
            </label>
            <textarea
              id="text-input"
              className={
                "w-full border rounded p-2 font-mono text-sm text-gray-900 bg-white " +
                (overLimit ? "border-red-400 focus:outline-red-400" : "border-gray-300")
              }
              rows={3}
              placeholder="Type one or more sentences here…"
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                setSelectedIdx(null);
                resetToIdle();
              }}
              disabled={isRecording || isProcessing}
            />
            <p className={`text-right text-xs ${overLimit ? "text-red-500 font-medium" : "text-gray-400"}`}>
              {charCount} / {MAX_CHARS}
            </p>
          </div>

          {/* sentence list */}
          {text.trim().length > 0 && !overLimit && (
            <div className="space-y-1">
              <p className="text-sm text-gray-500">Select a sentence to practise:</p>
              <SentenceList
                text={text}
                selected={selectedIdx}
                onChange={(i) => {
                  setSelectedIdx(i);
                  resetToIdle();
                }}
              />
            </div>
          )}

          {overLimit && (
            <p className="text-sm text-red-500">
              Text exceeds {MAX_CHARS} characters. Please shorten it before recording.
            </p>
          )}
        </>
      )}

      {/* Bilingual mode */}
      {mode === "bilingual" && (
        <div className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="bilingual-input" className="block font-medium">
              Paste Spanish–English sentence pairs
            </label>
            <textarea
              id="bilingual-input"
              className="w-full border rounded p-2 font-mono text-sm text-gray-900 bg-white border-gray-300"
              rows={6}
              placeholder={`Iré a Madrid la semana que viene. I will go to Madrid next week.\n2 Él comerá con nosotros. He'll have lunch with us.`}
              value={bilingualText}
              onChange={(e) => {
                setBilingualText(e.target.value);
                setSelectedPairIdx(null);
                resetToIdle();
              }}
              disabled={isRecording || isProcessing}
            />
          </div>
          {pairs.length > 0 && (
            <div className="space-y-1">
              <p className="text-sm text-gray-500">Select an English sentence to practise:</p>
              <BilingualSentenceList
                pairs={pairs}
                selected={selectedPairIdx}
                onChange={(i) => {
                  setSelectedPairIdx(i);
                  resetToIdle();
                }}
              />
            </div>
          )}
        </div>
      )}

      {/* recording controls */}
      {!isPreview && status !== "done" && (
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
            {status === "idle" && (selectedSentence ? "Ready — press Record." : "Select a sentence first.")}
            {status === "recording" && "Recording… press Stop when done."}
            {status === "processing" && "Sending to backend…"}
            {status === "error" && "Something went wrong."}
          </span>
        </div>
      )}

      {/* audio preview */}
      {isPreview && audioUrl && (
        <div className="space-y-3 rounded border border-gray-200 bg-gray-50 p-4">
          <p className="text-sm font-medium text-gray-700">Listen before sending:</p>
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <audio controls src={audioUrl} className="w-full" />
          <div className="flex gap-3">
            <button
              onClick={sendAudio}
              className="px-4 py-2 bg-blue-600 text-white rounded text-sm"
            >
              Send
            </button>
            <button
              onClick={resetToIdle}
              className="px-4 py-2 border border-gray-300 rounded text-sm hover:bg-gray-100"
            >
              Re-record
            </button>
          </div>
        </div>
      )}

      {/* error message */}
      {errorMsg && (
        <div className="border border-red-300 bg-red-50 text-red-700 rounded p-3 text-sm">
          {errorMsg}
        </div>
      )}

      {/* feedback panel */}
      {result && status === "done" && (
        <FeedbackPanel result={result} onReRecord={resetToIdle} />
      )}
    </main>
  );
}
