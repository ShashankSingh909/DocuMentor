"use client";

import { useState } from "react";
import { Globe, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { addCustomDoc } from "@/lib/api";

interface AddUrlFormProps {
  onSuccess: () => void;
}

const CATEGORIES = ["framework", "language", "database", "tool", "library", "other"];

export function AddUrlForm({ onSuccess }: AddUrlFormProps) {
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("framework");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() || !name.trim()) return;

    setLoading(true);
    setMessage(null);

    // Generate a doc_id from name
    const docId = name.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");

    try {
      const result = await addCustomDoc({ url: url.trim(), name: name.trim(), doc_id: docId, category });
      setMessage({ type: "success", text: `Ingested "${name}" — ${result.chunk_count} chunks created` });
      setUrl("");
      setName("");
      onSuccess();
    } catch (e) {
      setMessage({ type: "error", text: e instanceof Error ? e.message : "Failed to add documentation" });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="url">Documentation URL</Label>
          <Input
            id="url"
            type="url"
            placeholder="https://docs.example.com/guide"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="doc-name">Display Name</Label>
          <Input
            id="doc-name"
            placeholder="My Framework Docs"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>
      </div>

      <div className="flex items-end gap-4">
        <div className="space-y-1.5 w-48">
          <Label>Category</Label>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {CATEGORIES.map((c) => (
                <SelectItem key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Button type="submit" disabled={loading || !url || !name} className="gap-2">
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Globe className="h-4 w-4" />}
          {loading ? "Scraping…" : "Scrape & Ingest"}
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
