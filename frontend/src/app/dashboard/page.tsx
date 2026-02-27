"use client";

import { LayoutDashboard, RefreshCw, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { CatalogGrid } from "@/components/dashboard/CatalogGrid";
import { AddUrlForm } from "@/components/dashboard/AddUrlForm";
import { FileUploadForm } from "@/components/dashboard/FileUploadForm";
import { StatsPanel } from "@/components/dashboard/StatsPanel";
import { useDocSources } from "@/hooks/useDocSources";

export default function DashboardPage() {
  const { sources, loading, error, refetch, triggerIngest, triggerRemove } = useDocSources();

  return (
    <div className="mx-auto max-w-screen-xl px-4 py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <LayoutDashboard className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Admin Dashboard</h1>
            <p className="text-sm text-muted-foreground">
              Manage documentation sources and knowledge base
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={refetch} className="gap-2">
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      <Separator />

      {/* Documentation Catalog */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Documentation Catalog</h2>
        {loading ? (
          <div className="flex items-center gap-3 text-muted-foreground py-8">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading catalog…
          </div>
        ) : error ? (
          <div className="text-destructive text-sm py-4">
            {error} — Is the FastAPI backend running on port 8100?
          </div>
        ) : (
          <CatalogGrid sources={sources} onIngest={triggerIngest} onRemove={triggerRemove} />
        )}
      </section>

      <Separator />

      {/* Add Custom Documentation */}
      <section>
        <h2 className="text-lg font-semibold mb-1">Add Custom Documentation</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Scrape a documentation URL or upload a file to add it to the knowledge base.
        </p>
        <Tabs defaultValue="url">
          <TabsList>
            <TabsTrigger value="url">From URL</TabsTrigger>
            <TabsTrigger value="upload">Upload File</TabsTrigger>
          </TabsList>
          <TabsContent value="url" className="pt-4">
            <AddUrlForm onSuccess={refetch} />
          </TabsContent>
          <TabsContent value="upload" className="pt-4">
            <FileUploadForm onSuccess={refetch} />
          </TabsContent>
        </Tabs>
      </section>

      <Separator />

      {/* Statistics */}
      <section>
        <h2 className="text-lg font-semibold mb-4">Knowledge Base Statistics</h2>
        <StatsPanel />
      </section>
    </div>
  );
}
