import { MessageRole } from './message';

export interface ChatSessionSummary {
  id: string;
  title: string;
  updated_at?: string;
}

export interface ChatHistoryMessage {
  role: MessageRole;
  content: string;
  created_at?: string;
}

export interface ChatSessionDetail {
  id: string;
  title: string;
  messages: ChatHistoryMessage[];
}
