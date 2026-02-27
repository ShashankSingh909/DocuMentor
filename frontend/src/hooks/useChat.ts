"use client";

import { useState, useCallback } from "react";
import { askQuestion, generateCode } from "@/lib/api";
import type { ChatMessage, QuestionRequest, ResponseMode } from "@/lib/types";

let msgId = 0;
const nextId = () => `msg-${++msgId}`;

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (content: string, options: Omit<QuestionRequest, "question">) => {
      const userMsg: ChatMessage = {
        id: nextId(),
        role: "user",
        content,
        timestamp: new Date(),
      };

      const placeholderId = nextId();
      const placeholder: ChatMessage = {
        id: placeholderId,
        role: "assistant",
        content: "",
        timestamp: new Date(),
        isLoading: true,
      };

      setMessages((prev) => [...prev, userMsg, placeholder]);
      setLoading(true);
      setError(null);

      try {
        const mode: ResponseMode = options.response_mode ?? "smart_answer";
        let answer: string;
        let sources = [];
        let responseTime = 0;
        let providerUsed = "";

        if (mode === "code_generation") {
          const res = await generateCode({
            prompt: content,
            language: "python",
            technology: options.technology_filter,
            include_context: true,
            style: "complete",
          });
          answer = `\`\`\`${res.language}\n${res.code}\n\`\`\`${res.explanation ? `\n\n${res.explanation}` : ""}`;
          sources = res.sources;
          responseTime = res.response_time;
          providerUsed = res.provider_used;
        } else {
          const res = await askQuestion({ question: content, ...options });
          answer = res.answer;
          sources = res.sources;
          responseTime = res.response_time;
          providerUsed = res.provider_used;
        }

        setMessages((prev) =>
          prev.map((m) =>
            m.id === placeholderId
              ? {
                  ...m,
                  content: answer,
                  sources,
                  responseTime,
                  providerUsed,
                  mode,
                  isLoading: false,
                }
              : m
          )
        );
      } catch (e) {
        const errMsg = e instanceof Error ? e.message : "Request failed";
        setError(errMsg);
        setMessages((prev) =>
          prev.map((m) =>
            m.id === placeholderId
              ? { ...m, content: `Error: ${errMsg}`, isLoading: false }
              : m
          )
        );
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, loading, error, sendMessage, clearChat };
}
