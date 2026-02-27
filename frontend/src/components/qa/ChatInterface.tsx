"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { Send, Trash2, MessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MessageBubble } from "./MessageBubble";
import { useChat } from "@/hooks/useChat";
import type { ResponseMode } from "@/lib/types";

interface ChatInterfaceProps {
  settings: {
    provider: string;
    mode: ResponseMode;
    technology: string;
    searchK: number;
    webSearch: boolean;
    overlap: number;
  };
}

export function ChatInterface({ settings }: ChatInterfaceProps) {
  const { messages, loading, sendMessage, clearChat } = useChat();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    sendMessage(q, {
      response_mode: settings.mode,
      technology_filter: settings.technology !== "all" ? settings.technology : undefined,
      search_k: settings.searchK,
      enable_web_search: settings.webSearch,
      chunk_overlap: settings.overlap,
    });
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const placeholders: Record<ResponseMode, string> = {
    smart_answer: "Ask a question about your documentation… (Enter to send)",
    code_generation: "Describe the code you want to generate… (Enter to send)",
    detailed_sources: "Ask a detailed question with full source citations… (Enter to send)",
  };

  return (
    <div className="flex flex-col h-full">
      {/* Message list */}
      <ScrollArea className="flex-1 px-4 py-4">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center py-16 text-muted-foreground">
            <MessageSquare className="h-12 w-12 mb-4 opacity-20" />
            <p className="text-lg font-medium mb-1">Start a conversation</p>
            <p className="text-sm">Ask anything about your ingested documentation.</p>
            <p className="text-sm">Go to Dashboard to add docs first if needed.</p>
          </div>
        ) : (
          <div className="space-y-6 max-w-3xl mx-auto">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </ScrollArea>

      {/* Input area */}
      <div className="border-t border-border p-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex gap-2 items-end">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholders[settings.mode]}
              className="resize-none min-h-[52px] max-h-32"
              rows={2}
              disabled={loading}
            />
            <div className="flex flex-col gap-2">
              <Button
                onClick={handleSend}
                disabled={loading || !input.trim()}
                size="icon"
              >
                <Send className="h-4 w-4" />
              </Button>
              {messages.length > 0 && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={clearChat}
                  title="Clear chat"
                >
                  <Trash2 className="h-4 w-4 text-muted-foreground" />
                </Button>
              )}
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Shift+Enter for new line · Enter to send
          </p>
        </div>
      </div>
    </div>
  );
}
