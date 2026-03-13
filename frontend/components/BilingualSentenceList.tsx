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
      // Split on the first sentence-ending punctuation followed by a space
      const match = line.match(/^(.+?[.?!])\s+(.+)$/);
      if (!match) return [];
      return [{ spanish: match[1].trim(), english: match[2].trim() }];
    });
}

interface BilingualSentenceListProps {
  pairs: SentencePair[];
  selected: number | null;
  onChange: (i: number) => void;
}

export default function BilingualSentenceList({
  pairs,
  selected,
  onChange,
}: BilingualSentenceListProps) {
  if (pairs.length === 0) return null;

  return (
    <ol className="space-y-1">
      {pairs.map((pair, i) => (
        <li
          key={i}
          onClick={() => onChange(i)}
          className={
            "cursor-pointer rounded border px-3 py-2 text-sm transition-colors " +
            (selected === i
              ? "border-blue-400 bg-blue-50 ring-2 ring-blue-400"
              : "border-gray-200 bg-white hover:bg-gray-50")
          }
        >
          <div className="grid grid-cols-2 gap-4">
            <span className="text-gray-400 italic">{pair.spanish}</span>
            <span className="text-gray-900 font-medium">{pair.english}</span>
          </div>
        </li>
      ))}
    </ol>
  );
}
