"use client";

import { AnalyzeResponse } from "../lib/api";
import FeedbackPanel from "./FeedbackPanel";

export interface SentencePair {
    spanish: string;
    english: string;
}

export function parseBilingualText(text: string): SentencePair[] {
    return text
        .split("\n")
        .map((line) => line.trim().replace(/^\d+\s+/, ""))
        .filter(Boolean)
        .flatMap((line) => {
            const match = line.match(/^(.+?[.?!])\s+(.+)$/);
            if (!match) return [];
            return [{ spanish: match[1].trim(), english: match[2].trim() }];
        });
}

type RecStatus = "idle" | "recording" | "preview" | "processing" | "done" | "error";

const MAX_SENTENCE_CHARS = 200;

interface BilingualSentenceListProps {
    pairs: SentencePair[];
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
}

export default function BilingualSentenceList({
    pairs,
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
}: BilingualSentenceListProps) {
    if (pairs.length === 0) return null;

    return (
        <ol className="space-y-2">
            {pairs.map((pair, i) => {
                const isActive = selected === i;
                const isRowRecording = isActive && status === "recording";
                const isRowProcessing = isActive && status === "processing";
                const isRowPreview = isActive && status === "preview";
                const hasResult = i in results;
                const tooLong = pair.english.length > MAX_SENTENCE_CHARS;

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
                        {/* pair text + record/stop button */}
                        <div className="flex items-center justify-between gap-3">
                            <div className="grid grid-cols-2 gap-4 flex-1 min-w-0">
                                <span className="text-gray-400 italic">{pair.spanish}</span>
                                <span className="text-gray-900 font-medium">{pair.english}</span>
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

                        {/* phoneme preview chips (English side only) */}
                        {Object.keys(previewPhonemes).length > 0 && (
                            <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                                {pair.english
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
                                Sentence too long ({pair.english.length}/{MAX_SENTENCE_CHARS} chars) — shorten it to record.
                            </p>
                        )}

                        {isRowProcessing && (
                            <p className="mt-1 text-xs text-gray-400 italic">Processing…</p>
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
