"use client";

import { useState } from "react";
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
  previewPhonemes?: Record<string, string[]>;
  onRecord: (i: number) => void;
  onStop: () => void;
  onSend: () => void;
  onReRecord: (i: number) => void;
  onEditSentence?: (i: number, text: string) => void;
}

export default function SentenceList({
  sentences,
  selected,
  status,
  audioUrl,
  sentenceAudioUrls,
  results,
  isAnyBusy,
  previewPhonemes = {},
  onRecord,
  onStop,
  onSend,
  onReRecord,
  onEditSentence,
}: SentenceListProps) {
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [editValue, setEditValue] = useState("");

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
                {editingIdx === i ? (
                  <input
                    autoFocus
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        onEditSentence?.(i, editValue.trim() || sentence);
                        setEditingIdx(null);
                      } else if (e.key === "Escape") {
                        setEditingIdx(null);
                      }
                    }}
                    onBlur={() => {
                      onEditSentence?.(i, editValue.trim() || sentence);
                      setEditingIdx(null);
                    }}
                    className="flex-1 min-w-0 border-b border-blue-400 bg-transparent text-sm text-gray-900 outline-none"
                  />
                ) : (
                  <>
                    <span className="text-gray-900">{sentence}</span>
                    {onEditSentence && !isAnyBusy && !isRowRecording && !isRowProcessing && (
                      <button
                        onClick={() => { setEditingIdx(i); setEditValue(sentence); }}
                        title="Edit sentence"
                        className="flex-shrink-0 text-gray-300 hover:text-gray-500 text-xs leading-none"
                      >
                        ✏️
                      </button>
                    )}
                  </>
                )}
                {isRowProcessing && (
                  <span className="ml-1 text-xs text-gray-400 italic">Processing…</span>
                )}
              </div>
              <div className="flex-shrink-0 flex gap-1 items-center">
                {isRowRecording ? (
                  <button
                    onClick={onStop}
                    className="px-2.5 py-1 bg-red-600 text-white rounded text-xs font-medium"
                  >
                    ⏹ Stop
                  </button>
                ) : isRowPreview ? (
                  <>
                    <button
                      onClick={onSend}
                      className="px-2.5 py-1 bg-blue-600 text-white rounded text-xs font-medium"
                    >
                      ✓ Send
                    </button>
                    <button
                      onClick={() => onReRecord(i)}
                      title="Re-record"
                      className="px-2.5 py-1 border border-gray-300 rounded text-xs text-gray-600 hover:bg-gray-100"
                    >
                      🎤
                    </button>
                  </>
                ) : isRowProcessing ? (
                  <span className="px-2.5 py-1 text-xs text-gray-400">⌛</span>
                ) : (
                  <button
                    onClick={hasResult ? () => onReRecord(i) : () => onRecord(i)}
                    disabled={isAnyBusy || tooLong}
                    title={
                      tooLong
                        ? `Sentence exceeds ${MAX_SENTENCE_CHARS} characters`
                        : hasResult
                        ? "Re-record"
                        : "Record"
                    }
                    className="px-2.5 py-1 bg-blue-600 text-white rounded text-xs font-medium disabled:opacity-40"
                  >
                    🎤
                  </button>
                )}
              </div>
            </div>

            {/* phoneme preview chips */}
            {Object.keys(previewPhonemes).length > 0 && (
              <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                {sentence
                  .toLowerCase()
                  .replace(/[^a-z'\s]/g, "")
                  .split(/\s+/)
                  .filter(Boolean)
                  .map((word, wi) => {
                    const ph = previewPhonemes[word];
                    if (!ph) return null;
                    return (
                      <span key={wi} className="flex gap-0.5">
                        {ph.map((p, pi) => (
                          <span
                            key={pi}
                            className="inline-block rounded bg-gray-100 px-1 py-0.5 text-xs text-gray-500 font-mono"
                          >
                            {p}
                          </span>
                        ))}
                      </span>
                    );
                  })}
              </div>
            )}

            {tooLong && (
              <p className="mt-1 text-xs text-red-500">
                Sentence too long ({sentence.length}/{MAX_SENTENCE_CHARS} chars) — shorten it to record.
              </p>
            )}

            {/* inline audio preview — buttons are in the top-right zone above */}
            {isRowPreview && audioUrl && (
              <div className="mt-2 pt-2 border-t border-blue-200">
                {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
                <audio controls src={audioUrl} className="w-full" />
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
