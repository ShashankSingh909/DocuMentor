"use client";

import { DocCard } from "./DocCard";
import type { DocSource } from "@/lib/types";

interface CatalogGridProps {
  sources: DocSource[];
  onIngest: (id: string) => void;
  onRemove: (id: string) => void;
}

export function CatalogGrid({ sources, onIngest, onRemove }: CatalogGridProps) {
  // Group by category
  const groups = sources.reduce<Record<string, DocSource[]>>((acc, src) => {
    const cat = src.category.charAt(0).toUpperCase() + src.category.slice(1);
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(src);
    return acc;
  }, {});

  return (
    <div className="space-y-8">
      {Object.entries(groups).map(([category, srcs]) => (
        <div key={category}>
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-3">
            {category}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
            {srcs.map((src) => (
              <DocCard
                key={src.id}
                source={src}
                onIngest={onIngest}
                onRemove={onRemove}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
