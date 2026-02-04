import { Component, ChangeDetectionStrategy, signal, ViewChild, ElementRef, effect, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NeuralService } from '../../../../core/services/neural.service';

@Component({
  selector: 'app-neural-spine',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './neural-spine.component.html',
  styleUrl: './neural-spine.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NeuralSpineComponent {
  private neuralService = inject(NeuralService);
  
  @ViewChild('scrollContainer') scrollContainer!: ElementRef;
  
  userInput = ''; 
  isProcessing = signal(false);
  activeAgent = this.neuralService.activeAgent;
  
  messages = signal<Array<{role: string, content: string}>>([]); 

  constructor() {
    // History Loader Effect
    effect(() => {
      const agent = this.activeAgent();
      this.isProcessing.set(true);
      
      this.neuralService.getHistory(agent).subscribe({
        next: (history) => {
          if (history && history.length > 0) {
            this.messages.set(history);
          } else {
            // Cold Start: Welcome Message
            this.messages.set([
              { role: 'assistant', content: 'NEURAL_LINK_ESTABLISHED. I am Phylactery. How can I assist your operation today?' }
            ]);
          }
          this.isProcessing.set(false);
        },
        error: (err) => {
          console.warn('Failed to load history', err);
          this.isProcessing.set(false);
          // Fallback to welcome message on error (offline mode?)
           this.messages.set([
              { role: 'assistant', content: 'NEURAL_LINK_ESTABLISHED (OFFLINE MODE). System ready. (History fetch failed)' }
            ]);
        }
      });
    }, { allowSignalWrites: true });
    
    // Auto-scroll Effect
    effect(() => {
      this.messages(); // Dependency
      this.scrollToBottom();
    });
  }

  private scrollToBottom() {
    setTimeout(() => {
      if (this.scrollContainer) {
        const el = this.scrollContainer.nativeElement;
        el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
      }
    }, 100);
  }

  sendMessage() {
    const text = this.userInput.trim();
    if (!text || this.isProcessing()) return;

    // 1. UI Update (Operator message)
    this.messages.update(msgs => [...msgs, { role: 'user', content: text }]);
    this.userInput = '';
    this.isProcessing.set(true);

    // 2. Real Backend call
    const agent = this.neuralService.activeAgent();
    this.neuralService.sendMessage(agent, text).subscribe({
      next: (response: string) => {
        this.messages.update(msgs => [...msgs, { 
          role: 'assistant', 
          content: response 
        }]);
        this.isProcessing.set(false);
      },
      error: (err: any) => {
        console.error('Neural transmission failed', err);
        this.messages.update(msgs => [...msgs, { 
          role: 'assistant', 
          content: 'ERROR: Neural link compromised. Check console for terminal output.' 
        }]);
        this.isProcessing.set(false);
      }
    });
  }
}
