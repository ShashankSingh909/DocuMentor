"use client";

import { useState, useRef } from "react";
import { Upload, FileText, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { uploadDocument } from "@/lib/api";

interface FileUploadFormProps {
  onSuccess: () => void;
}

const ALLOWED_EXTS = [".txt", ".md", ".pdf", ".docx", ".doc", ".rtf", ".csv", ".xlsx", ".pptx", ".odt"];

export function FileUploadForm({ onSuccess }: FileUploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [sourceName, setSourceName] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) pickFile(dropped);
  };

  const pickFile = (f: File) => {
    const ext = "." + f.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTS.includes(ext)) {
      setMessage({ type: "error", text: `Unsupported format. Allowed: ${ALLOWED_EXTS.join(", ")}` });
      return;
    }
    setFile(f);
    if (!sourceName) setSourceName(f.name.replace(/\.[^.]+$/, "").replace(/[-_]/g, " "));
    setMessage(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !sourceName.trim()) return;

    setLoading(true);
    setMessage(null);

    try {
      const result = await uploadDocument(file, sourceName.trim());
      setMessage({ type: "success", text: `Uploaded "${sourceName}" — ${result.chunks_created} chunks created` });
      setFile(null);
      setSourceName("");
      onSuccess();
    } catch (e) {
      setMessage({ type: "error", text: e instanceof Error ? e.message : "Upload failed" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        className="border-2 border-dashed border-border rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
      >
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept={ALLOWED_EXTS.join(",")}
          onChange={(e) => { const f = e.target.files?.[0]; if (f) pickFile(f); }}
        />
        {file ? (
          <div className="flex items-center justify-center gap-3">
            <FileText className="h-8 w-8 text-primary" />
            <div className="text-left">
              <p className="font-medium text-sm">{file.name}</p>
              <p className="text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="ml-2"
              onClick={(e) => { e.stopPropagation(); setFile(null); }}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          <div>
            <Upload className="h-8 w-8 text-muted-foreground mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">Drop a file here or click to browse</p>
            <p className="text-xs text-muted-foreground mt-1">{ALLOWED_EXTS.join(" · ")}</p>
          </div>
        )}
      </div>

      {/* Source name + submit */}
      <div className="flex items-end gap-4">
        <div className="flex-1 space-y-1.5">
          <Label htmlFor="source-name">Source Name</Label>
          <Input
            id="source-name"
            placeholder="My Documentation"
            value={sourceName}
            onChange={(e) => setSourceName(e.target.value)}
            required
          />
        </div>
        <Button type="submit" disabled={loading || !file || !sourceName} className="gap-2">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Upload className="h-4 w-4" />}
          {loading ? "Uploading…" : "Upload & Ingest"}
        </Button>
      </div>

      {message && (
        <p className={`text-sm ${message.type === "success" ? "text-emerald-400" : "text-destructive"}`}>
          {message.text}
        </p>
      )}
    </form>
  );
}
