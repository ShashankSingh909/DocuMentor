"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LayoutDashboard, MessageSquare, BookOpen, Zap, Globe, Code2, Database } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getSystemStatus } from "@/lib/api";
import type { SystemStatus } from "@/lib/types";

export default function HomePage() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getSystemStatus()
      .then(setStatus)
      .catch(() => setError(true));
  }, []);

  return (
    <div className="mx-auto max-w-screen-xl px-4 py-16">
      {/* Hero */}
      <div className="text-center mb-16">
        <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-4 py-1.5 text-sm text-primary mb-6">
          <Zap className="h-3.5 w-3.5" />
          RAG-Powered Documentation Assistant
        </div>
        <h1 className="text-5xl font-extrabold tracking-tight mb-4 bg-gradient-to-r from-blue-400 via-violet-400 to-purple-400 bg-clip-text text-transparent">
          DocuMentor
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
          Ask questions about developer documentation in natural language.
          Powered by local LLMs, ChromaDB vector search, and smart chunking.
        </p>
        <div className="flex items-center justify-center gap-4">
          <Link href="/dashboard">
            <Button size="lg" className="gap-2">
              <LayoutDashboard className="h-4 w-4" />
              Open Dashboard
            </Button>
          </Link>
          <Link href="/qa">
            <Button size="lg" variant="outline" className="gap-2">
              <MessageSquare className="h-4 w-4" />
              Start Q&amp;A
            </Button>
          </Link>
        </div>
      </div>

      {/* Status Card */}
      <div className="mb-12">
        {error ? (
          <Card className="border-destructive/50 bg-destructive/10">
            <CardContent className="pt-6 text-center text-sm text-muted-foreground">
              Cannot connect to FastAPI backend at{" "}
              <code className="text-destructive">http://127.0.0.1:8100</code>.
              Run <code className="text-muted-foreground">python api_server.py</code> first.
            </CardContent>
          </Card>
        ) : status ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                Backend Connected
                <Badge variant="success" className="ml-auto">v{status.version}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Stat label="Total Chunks" value={status.total_chunks.toLocaleString()} icon={<Database className="h-4 w-4" />} />
                <Stat label="Technologies" value={status.technologies_loaded} icon={<BookOpen className="h-4 w-4" />} />
                <Stat label="LLM Provider" value={status.current_provider} icon={<Zap className="h-4 w-4" />} />
                <Stat label="Web Search" value={status.web_search_enabled ? "Enabled" : "Disabled"} icon={<Globe className="h-4 w-4" />} />
              </div>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center gap-3 text-muted-foreground text-sm">
                <div className="h-4 w-4 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                Connecting to backend...
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Feature grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[
          {
            icon: <LayoutDashboard className="h-6 w-6 text-primary" />,
            title: "Admin Dashboard",
            desc: "Browse 10+ pre-bundled documentation sources. Ingest with one click, add custom docs via URL scraping or file upload.",
            href: "/dashboard",
            cta: "Open Dashboard",
          },
          {
            icon: <MessageSquare className="h-6 w-6 text-violet-400" />,
            title: "Q&A Interface",
            desc: "Chat with your documentation. Smart answers, code generation, and detailed source citations. Technology-specific filtering.",
            href: "/qa",
            cta: "Start Chatting",
          },
          {
            icon: <Code2 className="h-6 w-6 text-emerald-400" />,
            title: "REST API",
            desc: "Full programmatic access via FastAPI. All endpoints documented at /docs. Rate limiting, auth, Prometheus metrics.",
            href: "http://127.0.0.1:8100/docs",
            cta: "View API Docs",
            external: true,
          },
        ].map((f) => (
          <Card key={f.title} className="hover:border-primary/50 transition-colors">
            <CardHeader>
              <div className="mb-2">{f.icon}</div>
              <CardTitle className="text-lg">{f.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">{f.desc}</p>
              <Link href={f.href} target={f.external ? "_blank" : undefined}>
                <Button variant="outline" size="sm" className="w-full">{f.cta}</Button>
              </Link>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value, icon }: { label: string; value: string | number; icon: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {icon}
        {label}
      </div>
      <div className="text-lg font-semibold">{value}</div>
    </div>
  );
}
