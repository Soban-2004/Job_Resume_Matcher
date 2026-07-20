"use client";

import { useCallback, useRef, useState } from "react";
import { FileText, UploadCloud, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface FileDropzoneProps {
  label: string;
  hint?: string;
  accept?: string;
  file: File | null;
  onChange: (file: File | null) => void;
}

export function FileDropzone({ label, hint, accept, file, onChange }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setIsDragging(false);
      const dropped = e.dataTransfer.files?.[0];
      if (dropped) onChange(dropped);
    },
    [onChange]
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
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "group relative flex min-h-[104px] cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-6 text-center transition-colors",
          isDragging
            ? "border-primary bg-primary/5"
            : "border-border hover:border-primary/50 hover:bg-accent/40"
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="hidden"
          onChange={(e) => onChange(e.target.files?.[0] ?? null)}
        />
        {file ? (
          <div className="flex w-full items-center justify-center gap-2 px-2">
            <FileText className="size-4 shrink-0 text-primary" />
            <span className="truncate text-sm font-medium text-foreground">{file.name}</span>
            <button
              type="button"
              aria-label="Remove file"
              onClick={(e) => {
                e.stopPropagation();
                onChange(null);
                if (inputRef.current) inputRef.current.value = "";
              }}
              className="ml-1 rounded-full p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            >
              <X className="size-3.5" />
            </button>
          </div>
        ) : (
          <>
            <UploadCloud className="size-6 text-muted-foreground group-hover:text-primary" />
            <div className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">Click to upload</span> or drag and drop
            </div>
            {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
          </>
        )}
      </div>
    </div>
  );
}
