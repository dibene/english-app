"use client";

import { useState } from "react";
import { AnalyzeResponse, feedbackBatch, FeedbackSentenceIn } from "../lib/api";

export interface SessionEntry {
    sentence: string;
    result: AnalyzeResponse;
}

interface SessionPanelProps {
    entries: SessionEntry[];
    onClear: () => void;
    onRemoveEntry: (index: number) => void;
}

function scoreColour(n: number): string {
    if (n >= 80) return "text-green-700 bg-green-100 border-green-300";
    if (n >= 50) return "text-yellow-700 bg-yellow-100 border-yellow-300";
    return "text-red-700 bg-red-100 border-red-300";
}

export default function SessionPanel({ entries, onClear, onRemoveEntry }: SessionPanelProps) {
    const [showJson, setShowJson] = useState(false);
    const [llmSuggestions, setLlmSuggestions] = useState<string[] | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [analyzeError, setAnalyzeError] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);

    if (entries.length === 0) return null;

    const feedbackData: FeedbackSentenceIn[] = entries.map((e) => ({
        expected_text: e.sentence,
        score: e.result.score,
        words: e.result.words,
    }));

    const jsonStr = JSON.stringify({ sentences: feedbackData }, null, 2);

    function copyJson() {
        navigator.clipboard.writeText(jsonStr).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        });
    }

    async function analyzeWithLlm() {
        setIsAnalyzing(true);
        setAnalyzeError(null);
        setLlmSuggestions(null);
        try {
            const suggestions = await feedbackBatch(feedbackData);
            setLlmSuggestions(suggestions);
        } catch (err) {
            setAnalyzeError(err instanceof Error ? err.message : "LLM request failed.");
        } finally {
            setIsAnalyzing(false);
        }
    }

    return (
        <div className="rounded border border-gray-200 bg-white p-4 space-y-4">
            <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-800">
                    Session Results ({entries.length})
                </h2>
                <button
                    onClick={onClear}
                    className="text-xs text-gray-400 hover:text-red-500 transition-colors"
                >
                    Clear all
                </button>
            </div>

            {/* per-sentence score list */}
            <ol className="space-y-1">
                {entries.map((entry, i) => (
                    <li key={i} className="flex items-center gap-3 text-sm">
                        <span
                            className={`flex-shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-bold ${scoreColour(entry.result.score)}`}
                        >
                            {entry.result.score}
                        </span>
                        <span className="flex-1 text-gray-700">{entry.sentence}</span>
                        <button
                            onClick={() => onRemoveEntry(i)}
                            title="Remove this result"
                            className="flex-shrink-0 text-gray-300 hover:text-red-500 transition-colors leading-none"
                            aria-label="Remove result"
                        >
                            ×
                        </button>
                    </li>
                ))}
            </ol>

            {/* action buttons */}
            <div className="flex flex-wrap gap-2">
                <button
                    onClick={() => setShowJson((v) => !v)}
                    className="px-3 py-1.5 text-sm rounded border border-gray-300 text-gray-700 hover:bg-gray-50"
                >
                    {showJson ? "Hide JSON" : "View JSON"}
                </button>
                <button
                    onClick={copyJson}
                    className="px-3 py-1.5 text-sm rounded border border-gray-300 text-gray-700 hover:bg-gray-50"
                >
                    {copied ? "Copied!" : "Copy JSON"}
                </button>
                <button
                    onClick={analyzeWithLlm}
                    disabled={isAnalyzing}
                    className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40"
                >
                    {isAnalyzing ? "Analyzing…" : "Analyze with LLM"}
                </button>
            </div>

            {/* JSON block */}
            {showJson && (
                <pre className="rounded bg-gray-900 text-green-400 p-3 text-xs overflow-auto max-h-72 font-mono whitespace-pre">
                    {jsonStr}
                </pre>
            )}

            {/* LLM error */}
            {analyzeError && (
                <p className="text-sm text-red-600">{analyzeError}</p>
            )}

            {/* LLM suggestions */}
            {llmSuggestions !== null && (
                <div className="space-y-1">
                    <p className="text-sm font-medium text-gray-600">LLM Feedback</p>
                    {llmSuggestions.length === 0 ? (
                        <p className="text-sm text-gray-400 italic">No suggestions returned.</p>
                    ) : (
                        <ul className="list-disc list-inside space-y-0.5">
                            {llmSuggestions.map((s, i) => (
                                <li key={i} className="text-sm text-gray-700">{s}</li>
                            ))}
                        </ul>
                    )}
                </div>
            )}
        </div>
    );
}
