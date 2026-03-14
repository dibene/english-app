"use client";

import { useState } from "react";

interface PhonemeEntry {
  ipa: string;
  arpabet: string;
  description: string;
  example: string;
}

const VOWELS: PhonemeEntry[] = [
  { ipa: "ɑ",  arpabet: "AA",  description: '"ah" open back',        example: "father" },
  { ipa: "æ",  arpabet: "AE",  description: 'short "a"',             example: "cat" },
  { ipa: "ʌ",  arpabet: "AH",  description: 'short "u"',             example: "cup" },
  { ipa: "ə",  arpabet: "AH0", description: "schwa (unstressed)",    example: "about" },
  { ipa: "ɔ",  arpabet: "AO",  description: '"aw" sound',            example: "law" },
  { ipa: "aʊ", arpabet: "AW",  description: '"ow" diphthong',        example: "cow" },
  { ipa: "aɪ", arpabet: "AY",  description: '"eye" diphthong',       example: "fly" },
  { ipa: "ɛ",  arpabet: "EH",  description: 'short "e"',             example: "bed" },
  { ipa: "ɝ",  arpabet: "ER",  description: '"er" r-colored vowel',  example: "bird" },
  { ipa: "eɪ", arpabet: "EY",  description: 'long "a" diphthong',    example: "say" },
  { ipa: "ɪ",  arpabet: "IH",  description: 'short "i"',             example: "bit" },
  { ipa: "i",  arpabet: "IY",  description: 'long "ee"',             example: "beat" },
  { ipa: "oʊ", arpabet: "OW",  description: 'long "o" diphthong',    example: "go" },
  { ipa: "ɔɪ", arpabet: "OY",  description: '"oy" diphthong',        example: "boy" },
  { ipa: "ʊ",  arpabet: "UH",  description: 'short "oo"',            example: "book" },
  { ipa: "u",  arpabet: "UW",  description: 'long "oo"',             example: "food" },
];

const CONSONANTS: PhonemeEntry[] = [
  { ipa: "b",  arpabet: "B",  description: "voiced bilabial stop",          example: "bed" },
  { ipa: "tʃ", arpabet: "CH", description: "voiceless affricate",           example: "choose" },
  { ipa: "d",  arpabet: "D",  description: "voiced alveolar stop",          example: "day" },
  { ipa: "ð",  arpabet: "DH", description: "voiced dental fricative",       example: "the" },
  { ipa: "f",  arpabet: "F",  description: "voiceless labiodental fricative", example: "fat" },
  { ipa: "ɡ",  arpabet: "G",  description: "voiced velar stop",              example: "get" },
  { ipa: "h",  arpabet: "HH", description: "voiceless glottal fricative",    example: "he" },
  { ipa: "dʒ", arpabet: "JH", description: "voiced affricate",               example: "judge" },
  { ipa: "k",  arpabet: "K",  description: "voiceless velar stop",           example: "key" },
  { ipa: "l",  arpabet: "L",  description: "lateral liquid",                 example: "leg" },
  { ipa: "m",  arpabet: "M",  description: "bilabial nasal",                 example: "me" },
  { ipa: "n",  arpabet: "N",  description: "alveolar nasal",                 example: "no" },
  { ipa: "ŋ",  arpabet: "NG", description: "velar nasal",                    example: "sing" },
  { ipa: "p",  arpabet: "P",  description: "voiceless bilabial stop",        example: "pet" },
  { ipa: "r",  arpabet: "R",  description: "alveolar approximant",           example: "red" },
  { ipa: "s",  arpabet: "S",  description: "voiceless alveolar fricative",   example: "sit" },
  { ipa: "ʃ",  arpabet: "SH", description: "voiceless palatal fricative",    example: "she" },
  { ipa: "t",  arpabet: "T",  description: "voiceless alveolar stop",        example: "top" },
  { ipa: "θ",  arpabet: "TH", description: "voiceless dental fricative",     example: "thin" },
  { ipa: "v",  arpabet: "V",  description: "voiced labiodental fricative",   example: "van" },
  { ipa: "w",  arpabet: "W",  description: "labio-velar approximant",        example: "wet" },
  { ipa: "j",  arpabet: "Y",  description: "palatal approximant",            example: "yet" },
  { ipa: "z",  arpabet: "Z",  description: "voiced alveolar fricative",      example: "zip" },
  { ipa: "ʒ",  arpabet: "ZH", description: "voiced palatal fricative",       example: "measure" },
];

function PhonemeTable({ entries }: { entries: PhonemeEntry[] }) {
  return (
    <table className="w-full text-xs border-collapse">
      <thead>
        <tr className="text-left text-gray-500 border-b border-gray-200">
          <th className="py-1 pr-3 font-semibold">IPA</th>
          <th className="py-1 pr-3 font-semibold">ARPAbet</th>
          <th className="py-1 pr-3 font-semibold">Description</th>
          <th className="py-1 font-semibold">Example</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((e) => (
          <tr key={e.arpabet} className="border-b border-gray-100 hover:bg-gray-50">
            <td className="py-1 pr-3 font-mono text-indigo-700 text-sm">{e.ipa}</td>
            <td className="py-1 pr-3 font-mono text-gray-500">{e.arpabet}</td>
            <td className="py-1 pr-3 text-gray-700">{e.description}</td>
            <td className="py-1 text-gray-500 italic">{e.example}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function IPAReference() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="px-3 py-1 rounded-md text-xs font-medium border bg-white text-gray-600 border-gray-300 hover:bg-gray-50 transition-colors"
        aria-expanded={open}
      >
        IPA guide 📖
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-2 z-50 w-[520px] max-h-[70vh] overflow-y-auto rounded-lg border border-gray-200 bg-white shadow-lg p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-gray-800">IPA Phoneme Reference (English)</h2>
            <button
              onClick={() => setOpen(false)}
              className="text-gray-400 hover:text-gray-600 text-lg leading-none"
              aria-label="Close IPA guide"
            >
              ×
            </button>
          </div>

          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Vowels</h3>
            <PhonemeTable entries={VOWELS} />
          </section>

          <section>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Consonants</h3>
            <PhonemeTable entries={CONSONANTS} />
          </section>
        </div>
      )}
    </div>
  );
}
