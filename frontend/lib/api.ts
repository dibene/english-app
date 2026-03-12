const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface PhonemeScore {
  phoneme: string;
  score: number;
}

export interface WordOut {
  expected_word: string | null;
  spoken_word: string | null;
  status: string;
  confidence: number | null;
  expected_phonemes: string[] | null;
  phoneme_scores: PhonemeScore[] | null;
}

export interface AnalyzeResponse {
  score: number;
  words: WordOut[];
  suggestions: string[];
}

export async function analyze(
  audio: Blob,
  sentence: string,
): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("audio_file", audio, "recording.webm");
  form.append("expected_text", sentence);

  const res = await fetch(`${API_URL}/analyze`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {
      // ignore parse error — keep the status fallback
    }
    throw new Error(detail);
  }

  return res.json() as Promise<AnalyzeResponse>;
}
