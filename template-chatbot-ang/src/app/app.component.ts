import { CommonModule } from '@angular/common';
import { HttpClientModule } from '@angular/common/http';
import {
  AfterViewInit,
  Component,
  ElementRef,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import { FormsModule } from '@angular/forms';

import { AiService, AiResponse } from './services/ai.service';
import { UiMessage } from './models/message';
import { MessageComponent } from './components/message/message.component';
import { VercelIconComponent } from './components/icons/vercel-icon/vercel-icon.component';
import { MasonryIconComponent } from './components/icons/masonry-icon/masonry-icon.component';
import { BotIconComponent } from './components/icons/bot-icon/bot-icon.component';

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
export class AppComponent implements AfterViewInit, OnDestroy {
  @ViewChild('messagesContainer') messagesContainer?: ElementRef<HTMLDivElement>;
  @ViewChild('messagesEnd') messagesEnd?: ElementRef<HTMLDivElement>;

  inputValue = '';
  messages: UiMessage[] = [];
  isProcessing = false;
  reflectionText = '';
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

    try {
      const responses = await this.aiService.sendMessage(trimmed);
      responses.forEach((response) => {
        this.addMessage(this.mapResponse(response));
      });
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

  private mapResponse(response: AiResponse): UiMessage {
    return {
      id: this.nextId(),
      role: 'assistant',
      text: response.text,
      places: response.places,
      viewUrl: response.viewUrl,
    };
  }

  private addMessage(message: UiMessage) {
    this.messages = [...this.messages, message];
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
