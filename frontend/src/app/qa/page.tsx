"use client";

import { useState } from "react";
import { SettingsSidebar } from "@/components/qa/SettingsSidebar";
import { ChatInterface } from "@/components/qa/ChatInterface";
import type { ResponseMode } from "@/lib/types";

interface Settings {
  provider: string;
  mode: ResponseMode;
  technology: string;
  searchK: number;
  webSearch: boolean;
  overlap: number;
}

const DEFAULT_SETTINGS: Settings = {
  provider: "ollama",
  mode: "smart_answer",
  technology: "all",
  searchK: 8,
  webSearch: false,
  overlap: 0,
};

export default function QAPage() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);

  const updateSettings = (partial: Partial<Settings>) => {
    setSettings((prev) => ({ ...prev, ...partial }));
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      <SettingsSidebar settings={settings} onChange={updateSettings} />
      <div className="flex-1 overflow-hidden">
        <ChatInterface settings={settings} />
      </div>
    </div>
  );
}
