"use client";

import { useCallback, useRef, useState } from "react";
import { FileText, UploadCloud, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface MultiFileDropzoneProps {
  label: string;
  hint?: string;
  accept?: string;
  files: File[];
  onChange: (files: File[]) => void;
}

export function MultiFileDropzone({ label, hint, accept, files, onChange }: MultiFileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback(
    (incoming: FileList | null) => {
      if (!incoming) return;
      const existingKeys = new Set(files.map((f) => `${f.name}-${f.size}`));
      const merged = [...files];
      for (const f of Array.from(incoming)) {
        const key = `${f.name}-${f.size}`;
        if (!existingKeys.has(key)) {
          merged.push(f);
          existingKeys.add(key);
        }
      }
      onChange(merged);
    },
    [files, onChange]
  );

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium text-foreground">{label}</label>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          addFiles(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "group flex min-h-[104px] cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50 hover:bg-accent/40"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple
          className="hidden"
          onChange={(e) => {
            addFiles(e.target.files);
            if (inputRef.current) inputRef.current.value = "";
          }}
        />
        <UploadCloud className="size-6 text-muted-foreground group-hover:text-primary" />
        <div className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">Click to upload</span> or drag and drop multiple
          resumes
        </div>
        {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
      </div>

      {files.length > 0 && (
        <ul className="flex flex-col gap-1.5 pt-1">
          {files.map((f, i) => (
            <li
              key={`${f.name}-${f.size}-${i}`}
              className="flex items-center gap-2 rounded-md border border-border bg-card px-3 py-1.5"
            >
              <FileText className="size-4 shrink-0 text-primary" />
              <span className="truncate text-sm text-foreground">{f.name}</span>
              <button
                type="button"
                aria-label={`Remove ${f.name}`}
                onClick={() => onChange(files.filter((_, idx) => idx !== i))}
                className="ml-auto rounded-full p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="size-3.5" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
