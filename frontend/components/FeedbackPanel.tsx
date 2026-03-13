import { AnalyzeResponse, WordOut } from "../lib/api";

// ── helpers ─────────────────────────────────────────────────────────────────

function scoreColour(n: number): string {
  if (n >= 80) return "text-green-700 bg-green-100 border-green-300";
  if (n >= 50) return "text-yellow-700 bg-yellow-100 border-yellow-300";
  return "text-red-700 bg-red-100 border-red-300";
}

function wordBg(status: string): string {
  switch (status) {
    case "ok":            return "bg-green-100 text-green-800";
    case "mispronounced": return "bg-yellow-100 text-yellow-800";
    case "missing":       return "bg-red-100 text-red-500 line-through opacity-60";
    case "inserted":      return "bg-blue-100 text-blue-800";
    default:              return "bg-gray-100 text-gray-700";
  }
}

function normalisePhoneme(p: string): string {
  return p.replace(/\d+$/, "").toLowerCase();
}

function phonemeDiffers(expected: string, spoken: string): boolean {
  return normalisePhoneme(expected) !== spoken.toLowerCase();
}

// ── PhonemeChip ──────────────────────────────────────────────────────────────

interface PhonemeChipProps {
  expected: string;
  score: number | null;   // null = no score data (Deepgram fallback)
  spoken: string | null;  // null = no spoken data
}

function PhonemeChip({ expected, score, spoken }: PhonemeChipProps) {
  const label = normalisePhoneme(expected).toUpperCase();
  const chipColour =
    score === null
      ? "bg-gray-100 text-gray-500 border-gray-300"
      : scoreColour(score);

  const showSpoken =
    spoken !== null && phonemeDiffers(expected, spoken);

  return (
    <div className="flex flex-col items-center">
      <span className={`rounded border px-1 py-0.5 text-xs font-mono font-semibold ${chipColour}`}>
        {label}
      </span>
      {showSpoken && (
        <span className="mt-0.5 text-[10px] text-gray-400 font-mono">
          {spoken.toLowerCase()}
        </span>
      )}
    </div>
  );
}

// ── WordCard ─────────────────────────────────────────────────────────────────

function WordCard({ word }: { word: WordOut }) {
  const hasPhonemes =
    word.expected_phonemes !== null && word.expected_phonemes.length > 0;

  return (
    <div className="flex flex-col items-center gap-1">
      {/* word pill */}
      <span className={`rounded px-2 py-0.5 text-sm font-medium ${wordBg(word.status)}`}>
        {word.expected_word ?? word.spoken_word ?? "—"}
      </span>

      {/* phoneme row */}
      {hasPhonemes && (
        <div className="flex flex-wrap justify-center gap-1">
          {word.expected_phonemes!.map((exp, i) => {
            const ps = word.phoneme_scores?.[i] ?? null;
            return (
              <PhonemeChip
                key={i}
                expected={exp}
                score={ps?.score ?? null}
                spoken={ps?.phoneme ?? null}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── FeedbackPanel ────────────────────────────────────────────────────────────

interface FeedbackPanelProps {
  result: AnalyzeResponse;
  onReRecord: () => void;
}

export default function FeedbackPanel({ result, onReRecord }: FeedbackPanelProps) {
  const { score, words, suggestions } = result;
  const isSuccess =
    score === 100 || words.every((w) => w.status === "ok");

  return (
    <div className="space-y-4 rounded border border-gray-200 bg-white p-4">
      {/* score */}
      <div className="flex items-center gap-3">
        <span
          className={`rounded-full border px-4 py-1 text-2xl font-bold ${scoreColour(score)}`}
        >
          {score}
        </span>
        {isSuccess && (
          <span className="text-green-700 font-medium">Perfect pronunciation! 🎉</span>
        )}
      </div>

      {/* word row */}
      {words.length > 0 && (
        <div className="flex flex-wrap gap-3">
          {words.map((w, i) => (
            <WordCard key={i} word={w} />
          ))}
        </div>
      )}

      {/* suggestions */}
      {suggestions.length > 0 && (
        <div>
          <p className="text-sm font-medium text-gray-600 mb-1">Suggestions</p>
          <ul className="list-disc list-inside space-y-0.5">
            {suggestions.map((s, i) => (
              <li key={i} className="text-sm text-gray-700">{s}</li>
            ))}
          </ul>
        </div>
      )}

      {/* re-record */}
      <button
        onClick={onReRecord}
        className="px-4 py-2 rounded border border-gray-300 text-sm text-gray-700 hover:bg-gray-50"
      >
        Re-record
      </button>
    </div>
  );
}
