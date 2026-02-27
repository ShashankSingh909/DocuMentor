"use client";

import { useEffect, useState } from "react";
import { Zap, Globe, SlidersHorizontal } from "lucide-react";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { getProviders, getIngestedSources, switchProvider } from "@/lib/api";
import type { LLMProvider, DocSource, ResponseMode } from "@/lib/types";

interface Settings {
  provider: string;
  mode: ResponseMode;
  technology: string;
  searchK: number;
  webSearch: boolean;
  overlap: number;
}

interface SettingsSidebarProps {
  settings: Settings;
  onChange: (s: Partial<Settings>) => void;
}

export function SettingsSidebar({ settings, onChange }: SettingsSidebarProps) {
  const [providers, setProviders] = useState<LLMProvider[]>([]);
  const [ingested, setIngested] = useState<DocSource[]>([]);

  useEffect(() => {
    getProviders().then((r) => setProviders(r.providers)).catch(() => {});
    getIngestedSources().then(setIngested).catch(() => {});
  }, []);

  const handleProviderChange = async (p: string) => {
    onChange({ provider: p });
    switchProvider(p).catch(() => {});
  };

  return (
    <aside className="w-64 flex-shrink-0 border-r border-border h-full overflow-y-auto p-4 space-y-5">
      <div className="flex items-center gap-2 font-semibold text-sm">
        <SlidersHorizontal className="h-4 w-4 text-primary" />
        Settings
      </div>

      <Separator />

      {/* Provider */}
      <div className="space-y-2">
        <Label className="flex items-center gap-1.5 text-xs text-muted-foreground uppercase tracking-wider">
          <Zap className="h-3 w-3" /> AI Provider
        </Label>
        <Select value={settings.provider} onValueChange={handleProviderChange}>
          <SelectTrigger className="h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {providers.length > 0 ? (
              providers.map((p) => (
                <SelectItem key={p.name} value={p.name} disabled={!p.available}>
                  <span className="flex items-center gap-2 capitalize">
                    <span className={`h-1.5 w-1.5 rounded-full ${p.available ? "bg-emerald-500" : "bg-muted"}`} />
                    {p.name}
                  </span>
                </SelectItem>
              ))
            ) : (
              <SelectItem value={settings.provider}>{settings.provider}</SelectItem>
            )}
          </SelectContent>
        </Select>
      </div>

      {/* Response mode */}
      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground uppercase tracking-wider">Response Mode</Label>
        <Select value={settings.mode} onValueChange={(v) => onChange({ mode: v as ResponseMode })}>
          <SelectTrigger className="h-8 text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="smart_answer">Smart Answer</SelectItem>
            <SelectItem value="code_generation">Code Generation</SelectItem>
            <SelectItem value="detailed_sources">Detailed Sources</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Technology filter */}
      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground uppercase tracking-wider">Technology Filter</Label>
        <Select value={settings.technology} onValueChange={(v) => onChange({ technology: v })}>
          <SelectTrigger className="h-8 text-sm">
            <SelectValue placeholder="All technologies" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All technologies</SelectItem>
            {ingested.map((src) => (
              <SelectItem key={src.id} value={src.id}>
                {src.icon} {src.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {ingested.length === 0 && (
          <p className="text-xs text-muted-foreground">No docs ingested yet. Go to Dashboard first.</p>
        )}
      </div>

      <Separator />

      {/* Search K */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-xs text-muted-foreground uppercase tracking-wider">Results</Label>
          <Badge variant="outline" className="text-xs">{settings.searchK}</Badge>
        </div>
        <Slider
          min={3}
          max={15}
          step={1}
          value={[settings.searchK]}
          onValueChange={([v]) => onChange({ searchK: v })}
          className="w-full"
        />
        <div className="flex justify-between text-xs text-muted-foreground">
          <span>3</span><span>15</span>
        </div>
      </div>

      {/* Overlap */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Label className="text-xs text-muted-foreground uppercase tracking-wider">Overlap</Label>
          <Badge variant="outline" className="text-xs">{settings.overlap}</Badge>
        </div>
        <Slider
          min={0}
          max={5}
          step={1}
          value={[settings.overlap]}
          onValueChange={([v]) => onChange({ overlap: v })}
          className="w-full"
        />
      </div>

      <Separator />

      {/* Web search */}
      <div className="flex items-center justify-between">
        <Label className="flex items-center gap-1.5 text-sm cursor-pointer">
          <Globe className="h-3.5 w-3.5 text-blue-400" />
          Web Search
        </Label>
        <Switch
          checked={settings.webSearch}
          onCheckedChange={(v) => onChange({ webSearch: v })}
        />
      </div>
    </aside>
  );
}
