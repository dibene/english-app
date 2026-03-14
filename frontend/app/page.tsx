"use client";

import { useEffect, useRef, useState } from "react";
import { analyze, AnalyzeResponse } from "../lib/api";
import SentenceList, { splitSentences } from "../components/SentenceList";
import BilingualSentenceList, { parseBilingualText } from "../components/BilingualSentenceList";
import SessionPanel, { SessionEntry } from "../components/SessionPanel";

const MAX_CHARS = 500;

type RecorderStatus = "idle" | "recording" | "preview" | "processing" | "error";

export default function Home() {
  const [text, setText] = useState("");
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [sentenceResults, setSentenceResults] = useState<Record<number, AnalyzeResponse>>({});
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [mode, setMode] = useState<"free" | "bilingual">("free");
  const [bilingualText, setBilingualText] = useState("");
  const [selectedPairIdx, setSelectedPairIdx] = useState<number | null>(null);
  const [llmMode, setLlmMode] = useState<"disabled" | "per-sentence" | "per-text">("per-sentence");
  const [sessionResults, setSessionResults] = useState<SessionEntry[]>([]);
  const [sentenceAudioUrls, setSentenceAudioUrls] = useState<Record<number, string>>({});

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  // revoke object URL on unmount
  useEffect(() => {
    return () => {
      if (audioUrl) URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl]);

  // revoke stored sentence audio URLs on unmount
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => () => { Object.values(sentenceAudioUrls).forEach((u) => URL.revokeObjectURL(u)); }, []);

  const sentences = splitSentences(text.trim());
  const freeSentence = selectedIdx !== null ? (sentences[selectedIdx] ?? null) : null;

  const pairs = parseBilingualText(bilingualText);
  const bilingualSentence = selectedPairIdx !== null ? (pairs[selectedPairIdx]?.english ?? null) : null;

  const selectedSentence = mode === "free" ? freeSentence : bilingualSentence;

  function resetToIdle() {
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudioBlob(null);
    setAudioUrl(null);
    setErrorMsg(null);
    setStatus("idle");
  }

  function switchMode(newMode: "free" | "bilingual") {
    setMode(newMode);
    setSelectedIdx(null);
    setSelectedPairIdx(null);
    setSentenceResults({});
    setSentenceAudioUrls((prev) => { Object.values(prev).forEach((u) => URL.revokeObjectURL(u)); return {}; });
    resetToIdle();
  }

  async function startRecording(idx: number) {
    resetToIdle();
    if (mode === "free") setSelectedIdx(idx);
    else setSelectedPairIdx(idx);

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
    const activeIdx = mode === "free" ? selectedIdx : selectedPairIdx;
    if (activeIdx === null) return;
    setStatus("processing");
    try {
      const enableLlm = llmMode === "per-sentence" ? undefined : false;
      const data = await analyze(audioBlob, selectedSentence, enableLlm);
      setSentenceResults((prev) => ({ ...prev, [activeIdx]: data }));
      if (llmMode === "per-text") {
        setSessionResults((prev) => [
          ...prev.filter((e) => e.sentence !== selectedSentence),
          { sentence: selectedSentence, result: data },
        ]);
      }
      // persist audio for this sentence instead of revoking it
      if (audioUrl) setSentenceAudioUrls((prev) => ({ ...prev, [activeIdx]: audioUrl }));
      setAudioBlob(null);
      setAudioUrl(null);
      setErrorMsg(null);
      setStatus("idle");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Unexpected error from backend.");
      setStatus("error");
    }
  }

  function reRecordSentence(idx: number) {
    setSentenceResults((prev) => {
      const updated = { ...prev };
      delete updated[idx];
      return updated;
    });
    setSentenceAudioUrls((prev) => {
      if (prev[idx]) URL.revokeObjectURL(prev[idx]);
      const updated = { ...prev };
      delete updated[idx];
      return updated;
    });
    resetToIdle();
  }

  const isRecording = status === "recording";
  const isProcessing = status === "processing";
  const isPreview = status === "preview";
  const isAnyBusy = isRecording || isProcessing || isPreview;
  const charCount = text.length;
  const overLimit = charCount > MAX_CHARS;

  return (
    <main className="max-w-2xl mx-auto p-8 space-y-6">
      <h1 className="text-2xl font-bold">Read &amp; Improve</h1>

      {/* Input mode tabs */}
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

      {/* LLM mode selector */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-gray-500 font-medium">LLM feedback:</span>
        <div className="flex gap-1 rounded-lg bg-gray-100 p-1">
          {(["disabled", "per-sentence", "per-text"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setLlmMode(m)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${llmMode === m
                  ? "bg-white shadow text-gray-900"
                  : "text-gray-500 hover:text-gray-700"
                }`}
            >
              {m === "disabled" ? "Disabled" : m === "per-sentence" ? "Per sentence" : "Per text"}
            </button>
          ))}
        </div>
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
                setSentenceResults({});
                setSentenceAudioUrls((prev) => { Object.values(prev).forEach((u) => URL.revokeObjectURL(u)); return {}; });
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
              <SentenceList
                sentences={sentences}
                selected={selectedIdx}
                status={status}
                audioUrl={audioUrl}
                sentenceAudioUrls={sentenceAudioUrls}
                results={sentenceResults}
                isAnyBusy={isAnyBusy}
                rowDisabled={overLimit}
                onRecord={startRecording}
                onStop={stopRecording}
                onSend={sendAudio}
                onReRecord={reRecordSentence}
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
                setSentenceResults({});
                setSentenceAudioUrls((prev) => { Object.values(prev).forEach((u) => URL.revokeObjectURL(u)); return {}; });
                resetToIdle();
              }}
              disabled={isRecording || isProcessing}
            />
          </div>
          {pairs.length > 0 && (
            <div className="space-y-1">
              <BilingualSentenceList
                pairs={pairs}
                selected={selectedPairIdx}
                status={status}
                audioUrl={audioUrl}
                sentenceAudioUrls={sentenceAudioUrls}
                results={sentenceResults}
                isAnyBusy={isAnyBusy}
                onRecord={startRecording}
                onStop={stopRecording}
                onSend={sendAudio}
                onReRecord={reRecordSentence}
              />
            </div>
          )}
        </div>
      )}

      {/* error message */}
      {errorMsg && (
        <div className="border border-red-300 bg-red-50 text-red-700 rounded p-3 text-sm">
          {errorMsg}
        </div>
      )}

      {/* session panel for per-text mode */}
      {llmMode === "per-text" && (
        <SessionPanel
          entries={sessionResults}
          onClear={() => setSessionResults([])}
        />
      )}
    </main>
  );
}
