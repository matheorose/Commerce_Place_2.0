import { CommonModule } from '@angular/common';
import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

import { MessageRole, PlaceInfo } from '../../models/message';
import { BotIconComponent } from '../icons/bot-icon/bot-icon.component';
import { UserIconComponent } from '../icons/user-icon/user-icon.component';

@Component({
  selector: 'app-message',
  standalone: true,
  imports: [CommonModule, BotIconComponent, UserIconComponent],
  templateUrl: './message.component.html',
  styleUrls: ['./message.component.css'],
})
export class MessageComponent implements OnChanges {
  @Input() role: MessageRole = 'assistant';
  @Input() text?: string;
  @Input() places?: PlaceInfo[];
  @Input() viewUrl?: string;
  @Input() thinkingTimeSeconds?: number;

  formattedText?: SafeHtml;

  constructor(private readonly sanitizer: DomSanitizer) {}

  ngOnChanges(_changes: SimpleChanges): void {
    this.formattedText = this.renderRichText(this.text ?? '');
  }

  private renderRichText(text: string): SafeHtml {
    if (!text) {
      return this.sanitizer.bypassSecurityTrustHtml('');
    }

    const escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    const bold = escaped.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    const italic = bold.replace(/\*(.+?)\*/g, '<em>$1</em>');
    const code = italic.replace(/`([^`]+)`/g, '<code>$1</code>');
    const withBreaks = code.replace(/\n/g, '<br />');

    return this.sanitizer.bypassSecurityTrustHtml(`<p>${withBreaks}</p>`);
  }
}
