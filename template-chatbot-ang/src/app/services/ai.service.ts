import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../environments/environment';
import { PlaceInfo } from '../models/message';
import { ChatSessionSummary, type ChatSessionDetail } from '../models/chat-session';

export type AiResponse = {
  kind: 'text';
  text: string;
  places?: PlaceInfo[];
  viewUrl?: string;
  sessionId?: string;
};

interface BackendData {
  count: number;
  bbox: Record<string, number>;
  places: PlaceInfo[];
  result_file: string;
  result_filename: string;
  view_file?: string;
}

interface BackendResponse {
  success: boolean;
  answer?: string;
  message?: string;
  parsed?: Record<string, unknown>;
  data?: BackendData;
  session_id?: string;
}

interface BackendHistoryMessage {
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
}

interface BackendSessionDetail {
  id: string;
  title: string;
  messages: BackendHistoryMessage[];
}

@Injectable({ providedIn: 'root' })
export class AiService {
  private sessionId?: string;

  constructor(private readonly http: HttpClient) {}

  setSession(sessionId: string | undefined) {
    this.sessionId = sessionId;
  }

  resetSession() {
    this.sessionId = undefined;
  }

  getSessionId() {
    return this.sessionId;
  }

  async sendMessage(message: string): Promise<AiResponse[]> {
    const body = { message, session_id: this.sessionId };
    const response = await firstValueFrom(
      this.http.post<BackendResponse>(`${environment.apiBaseUrl}/api/chat`, body),
    );

    if (!response.success) {
      return [
        {
          kind: 'text',
          text:
            response.message ??
            'Impossible de traiter la demande. Vérifiez le backend.',
        },
      ];
    }

    this.sessionId = response.session_id ?? this.sessionId;

    if (!response.data) {
      return [
        {
          kind: 'text',
          text:
            response.answer ??
            response.message ??
            'Requête traitée sans données spécifiques.',
          sessionId: this.sessionId,
        },
      ];
    }

    const viewUrl = response.data.view_file
      ? `${environment.apiBaseUrl}/api/views/${response.data.view_file}`
      : undefined;

    return [
      {
        kind: 'text',
        text: response.answer ?? 'Requête traitée avec succès.',
        places: response.data.places,
        viewUrl,
        sessionId: this.sessionId,
      },
    ];
  }

  async listSessions(): Promise<ChatSessionSummary[]> {
    const url = `${environment.apiBaseUrl}/api/chat/sessions`;
    return firstValueFrom(this.http.get<ChatSessionSummary[]>(url));
  }

  async fetchSession(sessionId: string): Promise<ChatSessionDetail> {
    const url = `${environment.apiBaseUrl}/api/chat/sessions/${sessionId}`;
    const detail = await firstValueFrom(this.http.get<BackendSessionDetail>(url));
    return {
      id: detail.id,
      title: detail.title,
      messages: detail.messages ?? [],
    };
  }
}
