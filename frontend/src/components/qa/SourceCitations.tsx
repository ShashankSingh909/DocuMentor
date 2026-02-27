"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { SourceChunk } from "@/lib/types";

interface SourceCitationsProps {
  sources: SourceChunk[];
}

export function SourceCitations({ sources }: SourceCitationsProps) {
  const [expanded, setExpanded] = useState(false);

  if (!sources.length) return null;

  // Group by technology
  const groups = sources.reduce<Record<string, SourceChunk[]>>((acc, s) => {
    const tech = s.metadata.technology ?? "unknown";
    if (!acc[tech]) acc[tech] = [];
    acc[tech].push(s);
    return acc;
  }, {});

  return (
    <div className="mt-3 border border-border rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-2 bg-muted/50 hover:bg-muted transition-colors text-sm"
      >
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground">Sources</span>
          {Object.entries(groups).map(([tech, chunks]) => (
            <Badge key={tech} variant="secondary" className="text-xs capitalize">
              {tech} · {chunks.length}
            </Badge>
          ))}
        </div>
        {expanded ? <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />}
      </button>

      {expanded && (
        <div className="divide-y divide-border max-h-64 overflow-y-auto">
          {sources.map((src, i) => (
            <div key={i} className="px-3 py-2 space-y-1">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  <Badge variant="info" className="text-xs capitalize">{src.metadata.technology ?? "—"}</Badge>
                  {src.metadata.title && (
                    <span className="text-xs text-muted-foreground truncate max-w-[200px]">{src.metadata.title}</span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {src.score !== undefined && (
                    <span className="text-xs text-muted-foreground">{(src.score * 100).toFixed(0)}%</span>
                  )}
                  {src.metadata.url && (
                    <a href={src.metadata.url} target="_blank" rel="noopener noreferrer">
                      <ExternalLink className="h-3 w-3 text-muted-foreground hover:text-primary" />
                    </a>
                  )}
                </div>
              </div>
              <p className="text-xs text-muted-foreground line-clamp-2">{src.content}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
