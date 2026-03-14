"use client";

import { AnalyzeResponse } from "../lib/api";
import FeedbackPanel from "./FeedbackPanel";

export function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.?!])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

const MAX_SENTENCE_CHARS = 200;

type RecStatus = "idle" | "recording" | "preview" | "processing" | "done" | "error";

interface SentenceListProps {
  sentences: string[];
  selected: number | null;
  status: RecStatus;
  audioUrl: string | null;
  sentenceAudioUrls: Record<number, string>;
  results: Record<number, AnalyzeResponse>;
  isAnyBusy: boolean;
  onRecord: (i: number) => void;
  onStop: () => void;
  onSend: () => void;
  onReRecord: (i: number) => void;
}

export default function SentenceList({
  sentences,
  selected,
  status,
  audioUrl,
  sentenceAudioUrls,
  results,
  isAnyBusy,
  onRecord,
  onStop,
  onSend,
  onReRecord,
}: SentenceListProps) {
  if (sentences.length === 0) return null;

  return (
    <ol className="space-y-2">
      {sentences.map((sentence, i) => {
        const isActive = selected === i;
        const isRowRecording = isActive && status === "recording";
        const isRowProcessing = isActive && status === "processing";
        const isRowPreview = isActive && status === "preview";
        const hasResult = i in results;
        const tooLong = sentence.length > MAX_SENTENCE_CHARS;

        return (
          <li
            key={i}
            className={
              "rounded border px-3 py-2 text-sm transition-colors " +
              (isActive
                ? "border-blue-400 bg-blue-50 ring-2 ring-blue-400"
                : "border-gray-200 bg-white")
            }
          >
            {/* sentence text + record/stop button */}
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <span className="flex-shrink-0 text-xs text-gray-400">{i + 1}.</span>
                <span className="text-gray-900">{sentence}</span>
                {isRowProcessing && (
                  <span className="ml-1 text-xs text-gray-400 italic">Processing…</span>
                )}
              </div>
              <div className="flex-shrink-0">
                {isRowRecording ? (
                  <button
                    onClick={onStop}
                    className="px-2.5 py-1 bg-red-600 text-white rounded text-xs font-medium"
                  >
                    ⏹ Stop
                  </button>
                ) : (
                  <button
                    onClick={() => onRecord(i)}
                    disabled={isAnyBusy || isRowProcessing || tooLong}
                    title={tooLong ? `Sentence exceeds ${MAX_SENTENCE_CHARS} characters` : "Record"}
                    className="px-2.5 py-1 bg-blue-600 text-white rounded text-xs font-medium disabled:opacity-40"
                  >
                    🎤
                  </button>
                )}
              </div>
            </div>

            {tooLong && (
              <p className="mt-1 text-xs text-red-500">
                Sentence too long ({sentence.length}/{MAX_SENTENCE_CHARS} chars) — shorten it to record.
              </p>
            )}

            {/* inline audio preview */}
            {isRowPreview && audioUrl && (
              <div className="mt-2 space-y-2 pt-2 border-t border-blue-200">
                {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                <audio controls src={audioUrl} className="w-full" />
                <div className="flex gap-2">
                  <button
                    onClick={onSend}
                    className="px-3 py-1.5 bg-blue-600 text-white rounded text-xs"
                  >
                    Send
                  </button>
                  <button
                    onClick={() => onReRecord(i)}
                    className="px-3 py-1.5 border border-gray-300 rounded text-xs text-gray-700 hover:bg-gray-100"
                  >
                    Re-record
                  </button>
                </div>
              </div>
            )}

            {/* inline result */}
            {hasResult && !isRowPreview && !isRowProcessing && (
              <div className="mt-2 pt-2 border-t border-gray-200 space-y-2">
                {sentenceAudioUrls[i] && (
                  // eslint-disable-next-line jsx-a11y/media-has-caption
                  <audio controls src={sentenceAudioUrls[i]} className="w-full" />
                )}
                <FeedbackPanel result={results[i]} onReRecord={() => onReRecord(i)} />
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
