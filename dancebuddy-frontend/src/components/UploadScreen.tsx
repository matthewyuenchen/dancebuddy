import { useState } from "react";
import { Dropzone } from "./Dropzone";

interface UploadScreenProps {
  onAnalyze: (userFile: File, referenceFile: File) => void;
}

export function UploadScreen({ onAnalyze }: UploadScreenProps) {
  const [userFile, setUserFile] = useState<File | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const ready = !!userFile && !!referenceFile;

  return (
    <section className="mx-auto w-full max-w-3xl px-5 py-10 sm:py-16">
      <div className="text-center">
        <span className="inline-flex items-center gap-2 rounded-full border border-line bg-surface px-3 py-1 text-xs font-medium text-muted">
          <span className="h-1.5 w-1.5 rounded-full bg-match" />
          Pose-based movement comparison
        </span>
        <h1 className="mt-5 font-display text-4xl leading-tight text-fg sm:text-5xl">
          See where your moves drift.
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-base text-muted">
          Upload your clip and the reference choreography. DanceBuddy lines them up and shows,
          side by side, exactly which movements are off.
        </p>
      </div>

      <div className="mt-10 grid gap-4 sm:grid-cols-2">
        <Dropzone
          label="Your video"
          hint="Drop or click · .mp4 / .mov · ≤60s"
          file={userFile}
          onFile={setUserFile}
        />
        <Dropzone
          label="Reference video"
          hint="Drop or click · .mp4 / .mov · ≤60s"
          file={referenceFile}
          onFile={setReferenceFile}
        />
      </div>

      <div className="mt-8 flex flex-col items-center gap-3">
        <button
          type="button"
          disabled={!ready}
          onClick={() => ready && onAnalyze(userFile, referenceFile)}
          className={`w-full max-w-xs cursor-pointer rounded-xl px-6 py-3 text-sm font-semibold transition-all duration-200 ${
            ready
              ? "bg-brand text-white shadow-lg shadow-brand/25 hover:bg-brand-strong"
              : "cursor-not-allowed bg-surface-2 text-muted"
          }`}
        >
          Analyze
        </button>
        <p className="text-xs text-muted">
          {ready ? "Ready — this can take a few seconds to a couple of minutes." : "Add both videos to continue."}
        </p>
      </div>
    </section>
  );
}
