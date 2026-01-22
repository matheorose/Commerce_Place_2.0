export type MessageRole = 'assistant' | 'user';

export interface PlaceInfo {
  id?: string;
  name?: string;
  lat?: number;
  lon?: number;
}

export interface UiMessage {
  id: number;
  role: MessageRole;
  text: string;
  places?: PlaceInfo[];
  viewUrl?: string;
  thinkingTimeSeconds?: number;
}
