"use client";

import { useEffect, useState } from "react";
import { Plus, Trash2, RefreshCw, CheckCircle2, XCircle, Clock, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useIngestionProgress } from "@/hooks/useIngestion";
import type { DocSource } from "@/lib/types";

interface DocCardProps {
  source: DocSource;
  onIngest: (id: string) => void;
  onRemove: (id: string) => void;
}

const STATUS_CONFIG = {
  completed: { label: "Ingested", variant: "success" as const, icon: CheckCircle2 },
  in_progress: { label: "Processing", variant: "warning" as const, icon: Loader2 },
  failed: { label: "Failed", variant: "destructive" as const, icon: XCircle },
  not_started: { label: "Not Added", variant: "secondary" as const, icon: Clock },
};

export function DocCard({ source, onIngest, onRemove }: DocCardProps) {
  const isActive = source.status === "in_progress";
  const { progress } = useIngestionProgress(source.id, isActive);

  const cfg = STATUS_CONFIG[source.status];
  const StatusIcon = cfg.icon;

  const pct = progress
    ? Math.round((progress.step / Math.max(progress.total_steps, 1)) * 100)
    : 0;

  return (
    <Card className="hover:border-primary/40 transition-colors">
      <CardContent className="pt-4 pb-4">
        {/* Header row */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-2xl flex-shrink-0">{source.icon}</span>
            <div className="min-w-0">
              <p className="font-semibold text-sm truncate">{source.name}</p>
              <p className="text-xs text-muted-foreground capitalize">{source.category}</p>
            </div>
          </div>
          <Badge variant={cfg.variant} className="flex-shrink-0 gap-1">
            <StatusIcon className={`h-3 w-3 ${isActive ? "animate-spin" : ""}`} />
            {cfg.label}
          </Badge>
        </div>

        {/* Chunk count */}
        {source.status === "completed" && (
          <p className="text-xs text-muted-foreground mb-3">
            {source.chunk_count.toLocaleString()} chunks
            {source.last_ingested && (
              <> · {new Date(source.last_ingested).toLocaleDateString()}</>
            )}
          </p>
        )}

        {/* Progress bar */}
        {isActive && (
          <div className="mb-3 space-y-1">
            <Progress value={pct} className="h-1.5" />
            <p className="text-xs text-muted-foreground">{progress?.message ?? "Processing…"}</p>
          </div>
        )}

        {/* Error */}
        {source.status === "failed" && source.error_message && (
          <p className="text-xs text-destructive mb-3 truncate">{source.error_message}</p>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          {source.status === "not_started" && (
            <Button size="sm" className="flex-1 gap-1" onClick={() => onIngest(source.id)}>
              <Plus className="h-3.5 w-3.5" /> Add
            </Button>
          )}
          {source.status === "completed" && (
            <Button
              size="sm"
              variant="outline"
              className="flex-1 gap-1 text-destructive hover:text-destructive"
              onClick={() => onRemove(source.id)}
            >
              <Trash2 className="h-3.5 w-3.5" /> Remove
            </Button>
          )}
          {source.status === "failed" && (
            <Button size="sm" variant="outline" className="flex-1 gap-1" onClick={() => onIngest(source.id)}>
              <RefreshCw className="h-3.5 w-3.5" /> Retry
            </Button>
          )}
          {isActive && (
            <Button size="sm" variant="ghost" className="flex-1" disabled>
              <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" /> Ingesting…
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
