function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.?!])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

interface SentenceListProps {
  text: string;
  selected: number | null;
  onChange: (i: number) => void;
}

export default function SentenceList({ text, selected, onChange }: SentenceListProps) {
  const sentences = splitSentences(text.trim());
  if (sentences.length === 0) return null;

  return (
    <ol className="space-y-1">
      {sentences.map((sentence, i) => (
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
          <span className="mr-2 text-xs text-gray-400">{i + 1}.</span>
          {sentence}
        </li>
      ))}
    </ol>
  );
}

export { splitSentences };
