export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: string;
}

export interface ThreadSummary {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
}

export interface ThreadRecord extends ThreadSummary {
  messages: ChatMessage[];
}

export interface ChatRequestBody {
  threadId: string;
  message: string;
}
