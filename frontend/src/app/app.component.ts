import { Component } from '@angular/core';
import { ChatService } from './services/chat.service';

interface Message {
  sender: 'user' | 'bot';
  text: string;
}

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent {
  title = 'NBA RAG Chat';
  messages: Message[] = [];
  userInput = '';
  loading = false;

  constructor(private chatService: ChatService) {}

  sendMessage(): void {
    const input = this.userInput.trim();
    if (!input) return;

    this.messages.push({ sender: 'user', text: input });
    this.userInput = '';
    this.loading = true;

    this.chatService.sendMessage(input).subscribe({
      next: (res: any) => {
        // handle structured response
        const answer = res?.answer ?? 'No answer received.';
        this.messages.push({ sender: 'bot', text: answer });
        this.loading = false;
      },
      error: (err) => {
        console.error(err);
        this.messages.push({ sender: 'bot', text: '⚠️ Error contacting server.' });
        this.loading = false;
      }
    });
  }
}
