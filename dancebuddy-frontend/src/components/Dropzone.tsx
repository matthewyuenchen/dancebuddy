import { useRef, useState } from "react";
import { FilmIcon, UploadIcon } from "../icons";

interface DropzoneProps {
  label: string;
  hint: string;
  file: File | null;
  onFile: (file: File | null) => void;
}

function isVideo(file: File): boolean {
  const name = file.name.toLowerCase();
  return file.type.startsWith("video/") || name.endsWith(".mp4") || name.endsWith(".mov");
}

function prettySize(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  return mb >= 1 ? `${mb.toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

export function Dropzone({ label, hint, file, onFile }: DropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [rejected, setRejected] = useState(false);

  function pick(f: File | null) {
    if (f && !isVideo(f)) {
      setRejected(true);
      return;
    }
    setRejected(false);
    onFile(f);
  }

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept="video/mp4,video/quicktime,.mp4,.mov"
        className="hidden"
        onChange={(e) => pick(e.target.files?.[0] ?? null)}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          pick(e.dataTransfer.files?.[0] ?? null);
        }}
        className={`group flex w-full cursor-pointer flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-all duration-200 ${
          dragging
            ? "border-brand bg-brand/10"
            : file
              ? "border-match/50 bg-surface"
              : "border-line bg-surface hover:border-brand/60 hover:bg-surface-2"
        }`}
      >
        <span
          className={`flex h-12 w-12 items-center justify-center rounded-full transition-colors ${
            file ? "bg-match/15 text-match" : "bg-surface-2 text-muted group-hover:text-brand"
          }`}
        >
          {file ? <FilmIcon width={22} height={22} /> : <UploadIcon width={22} height={22} />}
        </span>

        {file ? (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-fg">{file.name}</p>
            <p className="mt-0.5 text-xs text-muted">{prettySize(file.size)} · click to replace</p>
          </div>
        ) : (
          <div>
            <p className="text-sm font-semibold text-fg">{label}</p>
            <p className="mt-0.5 text-xs text-muted">{hint}</p>
          </div>
        )}
      </button>
      {rejected && (
        <p className="mt-2 text-center text-xs text-diverge">Please choose an .mp4 or .mov file.</p>
      )}
    </div>
  );
}
