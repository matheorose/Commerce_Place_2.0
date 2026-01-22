import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AiService, AiResponse } from './services/ai.service';
import { UiMessage } from './models/message';
import { MessageComponent } from './components/message/message.component';
import { VercelIconComponent } from './components/icons/vercel-icon/vercel-icon.component';
import { MasonryIconComponent } from './components/icons/masonry-icon/masonry-icon.component';
import { BotIconComponent } from './components/icons/bot-icon/bot-icon.component';
import { ChatSessionSummary } from './models/chat-session';

interface SuggestedAction {
  title: string;
  label: string;
  action: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    HttpClientModule,
    FormsModule,
    MessageComponent,
    VercelIconComponent,
    MasonryIconComponent,
    BotIconComponent,
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements AfterViewInit, OnDestroy, OnInit {
  @ViewChild('messagesContainer') messagesContainer?: ElementRef<HTMLDivElement>;
  @ViewChild('messagesEnd') messagesEnd?: ElementRef<HTMLDivElement>;

  inputValue = '';
  messages: UiMessage[] = [];
  isProcessing = false;
  reflectionText = '';
  sessions: ChatSessionSummary[] = [];
  selectedSessionId?: string;
  isSidebarOpen = true;
  private reflectionInterval?: ReturnType<typeof setInterval>;
  suggestedActions: SuggestedAction[] = [
    {
      title: 'Trouver',
      label: 'les boulangeries à Thann',
      action: 'Trouve les boulangeries à Thann',
    },
    {
      title: 'Lister',
      label: 'les pharmacies à Belfort',
      action: 'Liste les pharmacies à Belfort',
    },
    {
      title: 'Rechercher',
      label: 'des restaurants à Mulhouse',
      action: 'Je cherche des restaurants à Mulhouse',
    },
    {
      title: 'Analyser',
      label: "les boucheries autour de Paris",
      action: 'Trouve les boucheries à Paris dans un rayon de 5km',
    },
  ];

  private messageCounter = 0;
  private observer?: MutationObserver;

  constructor(private readonly aiService: AiService) {}

  async ngOnInit(): Promise<void> {
    await this.refreshSessions();
  }

  ngAfterViewInit(): void {
    if (!this.messagesContainer?.nativeElement) {
      return;
    }

    this.observer = new MutationObserver(() => this.scrollToBottom());
    this.observer.observe(this.messagesContainer.nativeElement, {
      childList: true,
      subtree: true,
    });
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }

  trackMessage(_index: number, message: UiMessage) {
    return message.id;
  }

  async onSubmit() {
    if (!this.inputValue.trim()) {
      return;
    }

    await this.sendMessage(this.inputValue);
  }

  async runAction(action: string) {
    await this.sendMessage(action);
  }

  async loadSession(sessionId: string) {
    if (this.selectedSessionId === sessionId && this.messages.length > 0) {
      return;
    }
    try {
      const detail = await this.aiService.fetchSession(sessionId);
      const restoredMessages = detail.messages.map((message, index) => ({
        id: index + 1,
        role: message.role,
        text: message.content,
      }));
      this.messages = restoredMessages;
      this.messageCounter = restoredMessages.length;
      this.selectedSessionId = detail.id;
      this.aiService.setSession(detail.id);
      setTimeout(() => this.scrollToBottom(), 0);
      await this.refreshSessions();
    } catch (error) {
      console.error('Impossible de charger la conversation', error);
    }
  }

  async startNewChat() {
    this.messages = [];
    this.inputValue = '';
    this.selectedSessionId = undefined;
    this.messageCounter = 0;
    this.aiService.resetSession();
    await this.refreshSessions();
  }

  isActiveSession(sessionId: string) {
    return this.selectedSessionId === sessionId;
  }

  toggleSidebar() {
    this.isSidebarOpen = !this.isSidebarOpen;
  }

  private async sendMessage(text: string) {
    if (this.isProcessing) {
      return;
    }

    this.isProcessing = true;
    this.startReflectionIndicator();
    const trimmed = text.trim();
    this.addMessage({
      id: this.nextId(),
      role: 'user',
      text: trimmed,
    });
    this.inputValue = '';

    const startedAt = performance.now();
    try {
      const responses = await this.aiService.sendMessage(trimmed);
      const elapsedSeconds = (performance.now() - startedAt) / 1000;
      responses.forEach((response) => {
        this.addMessage(this.mapResponse(response, elapsedSeconds));
      });
      this.selectedSessionId = this.aiService.getSessionId();
      await this.refreshSessions();
    } catch (error) {
      console.error(error);
      this.addMessage({
        id: this.nextId(),
        role: 'assistant',
        text: 'Something went wrong while processing your request.',
      });
    } finally {
      this.isProcessing = false;
      this.stopReflectionIndicator();
      this.scrollToBottom();
    }
  }

  private mapResponse(response: AiResponse, thinkingTimeSeconds?: number): UiMessage {
    return {
      id: this.nextId(),
      role: 'assistant',
      text: response.text,
      places: response.places,
      viewUrl: response.viewUrl,
      thinkingTimeSeconds,
    };
  }

  private addMessage(message: UiMessage) {
    this.messages = [...this.messages, message];
  }

  private async refreshSessions() {
    try {
      this.sessions = await this.aiService.listSessions();
    } catch (error) {
      console.error('Impossible de récupérer les conversations', error);
    }
  }

  private nextId() {
    this.messageCounter += 1;
    return this.messageCounter;
  }

  private scrollToBottom() {
    this.messagesEnd?.nativeElement.scrollIntoView({ behavior: 'smooth' });
  }

  private startReflectionIndicator() {
    const variants = ['Réflexion', 'Réflexion.', 'Réflexion..', 'Réflexion...'];
    let index = 0;
    this.reflectionText = variants[index];

    this.reflectionInterval = setInterval(() => {
      index = (index + 1) % variants.length;
      this.reflectionText = variants[index];
    }, 450);
  }

  private stopReflectionIndicator() {
    if (this.reflectionInterval) {
      clearInterval(this.reflectionInterval);
      this.reflectionInterval = undefined;
    }
    this.reflectionText = '';
  }
}
