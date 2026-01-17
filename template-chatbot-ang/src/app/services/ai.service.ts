import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../environments/environment';
import { PlaceInfo } from '../models/message';

export type AiResponse = {
  kind: 'text';
  text: string;
  places?: PlaceInfo[];
  viewUrl?: string;
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
}

@Injectable({ providedIn: 'root' })
export class AiService {
  constructor(private readonly http: HttpClient) {}

  async sendMessage(message: string): Promise<AiResponse[]> {
    const body = { message };
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

    if (!response.data) {
      return [
        {
          kind: 'text',
          text:
            response.answer ??
            response.message ??
            'Requête traitée sans données spécifiques.',
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
      },
    ];
  }
}
