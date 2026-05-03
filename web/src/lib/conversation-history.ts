import type { ModelMessage } from "ai";

import type { ChatMessage } from "./types";

const messageTokenOverhead = 4;
const approximateCharsPerToken = 4;
const omissionNotice = "\n\n[Earlier content omitted to fit the conversation token budget.]\n\n";

function estimateTextTokens(text: string): number {
  return Math.ceil(text.length / approximateCharsPerToken);
}

function estimateMessageTokens(message: Pick<ChatMessage, "content">): number {
  return messageTokenOverhead + estimateTextTokens(message.content);
}

function truncateContentToBudget(content: string, tokenBudget: number): string {
  const charBudget = Math.max(0, tokenBudget - messageTokenOverhead) * approximateCharsPerToken;

  if (content.length <= charBudget) return content;
  if (charBudget <= omissionNotice.length + 20) {
    return content.slice(0, charBudget);
  }

  const available = charBudget - omissionNotice.length;
  const headLength = Math.floor(available * 0.35);
  const tailLength = available - headLength;

  return `${content.slice(0, headLength)}${omissionNotice}${content.slice(-tailLength)}`;
}

function toModelMessage(message: ChatMessage): ModelMessage {
  return {
    role: message.role,
    content: message.content,
  };
}

export function buildBoundedModelMessages(
  messages: ChatMessage[],
  maxTokens: number,
): ModelMessage[] {
  const selected: ChatMessage[] = [];
  let remainingTokens = maxTokens;

  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    const tokenCount = estimateMessageTokens(message);

    if (tokenCount <= remainingTokens) {
      selected.unshift(message);
      remainingTokens -= tokenCount;
      continue;
    }

    if (!selected.length && remainingTokens > messageTokenOverhead) {
      selected.unshift({
        ...message,
        content: truncateContentToBudget(message.content, remainingTokens),
      });
    }

    break;
  }

  return selected.map(toModelMessage);
}
