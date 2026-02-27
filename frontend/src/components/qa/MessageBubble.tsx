"use client";

import { Bot, User, Clock, Loader2 } from "lucide-react";
import { SourceCitations } from "./SourceCitations";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { ChatMessage } from "@/lib/types";

const MODE_LABELS: Record<string, string> = {
  smart_answer: "Smart Answer",
  code_generation: "Code",
  detailed_sources: "Detailed",
};

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      {/* Avatar */}
      <div className={cn(
        "flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center text-xs",
        isUser ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
      )}>
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Content */}
      <div className={cn("max-w-[80%] space-y-1", isUser && "items-end flex flex-col")}>
        <div className={cn(
          "rounded-2xl px-4 py-3 text-sm",
          isUser
            ? "bg-primary text-primary-foreground rounded-tr-sm"
            : "bg-secondary text-secondary-foreground rounded-tl-sm"
        )}>
          {message.isLoading ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
              Thinking…
            </div>
          ) : (
            <FormattedContent content={message.content} />
          )}
        </div>

        {/* Meta */}
        {!isUser && !message.isLoading && (
          <div className="flex items-center gap-2 px-1 flex-wrap">
            {message.mode && (
              <Badge variant="outline" className="text-xs">{MODE_LABELS[message.mode] ?? message.mode}</Badge>
            )}
            {message.providerUsed && (
              <span className="text-xs text-muted-foreground capitalize">{message.providerUsed}</span>
            )}
            {message.responseTime !== undefined && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {message.responseTime.toFixed(2)}s
              </span>
            )}
          </div>
        )}

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="w-full">
            <SourceCitations sources={message.sources} />
          </div>
        )}
      </div>
    </div>
  );
}

function FormattedContent({ content }: { content: string }) {
  // Simple code block rendering
  const parts = content.split(/(```[\s\S]*?```)/g);
  return (
    <div className="space-y-2">
      {parts.map((part, i) => {
        if (part.startsWith("```")) {
          const lines = part.slice(3, -3).split("\n");
          const lang = lines[0].trim();
          const code = lines.slice(1).join("\n");
          return (
            <pre key={i} className="bg-background/50 rounded-lg p-3 overflow-x-auto text-xs font-mono">
              {lang && <div className="text-muted-foreground mb-1 text-xs">{lang}</div>}
              <code>{code}</code>
            </pre>
          );
        }
        // Inline code
        const inlineParts = part.split(/(`[^`]+`)/g);
        return (
          <p key={i} className="leading-relaxed whitespace-pre-wrap">
            {inlineParts.map((ip, j) =>
              ip.startsWith("`") && ip.endsWith("`") ? (
                <code key={j} className="bg-background/50 px-1.5 py-0.5 rounded text-xs font-mono">
                  {ip.slice(1, -1)}
                </code>
              ) : ip
            )}
          </p>
        );
      })}
    </div>
  );
}
