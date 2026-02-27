"use client";

import { useEffect, useState } from "react";
import { Database, Zap, Globe, Cpu } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { getSystemStatus, getTechnologies } from "@/lib/api";
import type { SystemStatus, TechnologyStats } from "@/lib/types";

export function StatsPanel() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [techs, setTechs] = useState<TechnologyStats[]>([]);

  useEffect(() => {
    getSystemStatus().then(setStatus).catch(() => {});
    getTechnologies().then(setTechs).catch(() => {});
  }, []);

  if (!status) return null;

  const ingested = techs.filter((t) => t.available);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Quick stats */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Knowledge Base</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <StatRow icon={<Database className="h-4 w-4 text-primary" />} label="Total Chunks" value={status.total_chunks.toLocaleString()} />
          <StatRow icon={<Globe className="h-4 w-4 text-violet-400" />} label="Technologies Ingested" value={status.technologies_loaded} />
          <StatRow icon={<Zap className="h-4 w-4 text-yellow-400" />} label="Active Provider" value={status.current_provider} />
          <StatRow icon={<Cpu className="h-4 w-4 text-emerald-400" />} label="Web Search" value={status.web_search_enabled ? "Enabled" : "Disabled"} />
        </CardContent>
      </Card>

      {/* Provider availability */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">LLM Providers</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {status.providers.map((p) => (
            <div key={p.name} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className={`h-2 w-2 rounded-full ${p.available ? "bg-emerald-500" : "bg-muted"}`} />
                <span className="text-sm capitalize">{p.name}</span>
                {p.model && <span className="text-xs text-muted-foreground">{p.model}</span>}
              </div>
              {p.is_current && <Badge variant="success">Active</Badge>}
              {!p.available && <Badge variant="secondary">Unavailable</Badge>}
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Per-tech breakdown */}
      {ingested.length > 0 && (
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Ingested Technologies</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y divide-border">
              {ingested.map((t) => (
                <div key={t.technology} className="flex items-center justify-between py-2">
                  <span className="text-sm capitalize">{t.technology}</span>
                  <span className="text-sm text-muted-foreground">{t.chunk_count.toLocaleString()} chunks</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {icon}
        {label}
      </div>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}
