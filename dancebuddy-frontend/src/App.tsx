import { useCallback, useState } from "react";
import type { AnalyzeResult } from "./api";
import { analyzeVideos } from "./api";
import { ResultsScreen } from "./components/ResultsScreen";
import { UploadScreen } from "./components/UploadScreen";
import { AlertIcon, SparkIcon } from "./icons";

type Screen = "upload" | "loading" | "results" | "error";

export default function App() {
  const [screen, setScreen] = useState<Screen>("upload");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [error, setError] = useState("");

  const handleAnalyze = useCallback(async (userFile: File, referenceFile: File) => {
    setError("");
    setScreen("loading");
    try {
      const r = await analyzeVideos(userFile, referenceFile);
      setResult(r);
      setScreen("results");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setScreen("error");
    }
  }, []);

  const reset = () => {
    setResult(null);
    setError("");
    setScreen("upload");
  };

  return (
    <div className="min-h-full">
      <header className="border-b border-line/60">
        <div className="mx-auto flex max-w-6xl items-center gap-2.5 px-5 py-4">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand/15 text-brand">
            <SparkIcon width={18} height={18} />
          </span>
          <span className="font-display text-lg text-fg">DanceBuddy</span>
        </div>
      </header>

      <main>
        {screen === "upload" && <UploadScreen onAnalyze={handleAnalyze} />}
        {screen === "loading" && <LoadingScreen />}
        {screen === "results" && result && <ResultsScreen result={result} onReset={reset} />}
        {screen === "error" && <ErrorScreen message={error} onBack={reset} />}
      </main>
    </div>
  );
}

function LoadingScreen() {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-5 py-24 text-center">
      <div className="flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-3 w-3 animate-bounce rounded-full bg-brand motion-reduce:animate-none"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
      <p className="mt-6 text-lg font-medium text-fg">Analyzing your moves…</p>
      <p className="mt-1 text-sm text-muted">
        Tracking body pose and lining up the two videos. This can take up to a couple of minutes.
      </p>
    </div>
  );
}

function ErrorScreen({ message, onBack }: { message: string; onBack: () => void }) {
  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-5 py-24 text-center">
      <span className="flex h-12 w-12 items-center justify-center rounded-full bg-diverge/15 text-diverge">
        <AlertIcon width={24} height={24} />
      </span>
      <p className="mt-5 text-lg font-medium text-fg">Couldn't analyze the videos</p>
      <p className="mt-2 text-sm text-muted">{message}</p>
      <button
        onClick={onBack}
        className="mt-6 cursor-pointer rounded-xl bg-brand px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-strong"
      >
        Try again
      </button>
    </div>
  );
}
