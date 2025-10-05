import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class TranscriptService {
  private ws?: WebSocket;

  partial$ = new BehaviorSubject<string>('');
  final$ = new BehaviorSubject<string>('');
  ready$ = new BehaviorSubject<boolean>(false);

  connect(language?: string) {
    this.ws = new WebSocket('ws://localhost:8000');
    this.ws.binaryType = 'arraybuffer';

    this.ws.onopen = () => {
      this.ws?.send(JSON.stringify({ type: 'start', language }));
    };

    this.ws.onmessage = (evt) => {
      if (typeof evt.data !== 'string') return;
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'ready') this.ready$.next(true);
        if (msg.type === 'partial') this.partial$.next(msg.text ?? '');
        if (msg.type === 'final') this.final$.next(msg.text ?? '');
      } catch {}
    };

    this.ws.onerror = () => this.ready$.next(false);
    this.ws.onclose = () => this.ready$.next(false);
  }

  sendAudioChunk(chunk: Blob) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    chunk.arrayBuffer().then((buf) => this.ws?.send(buf));
  }

  stop() {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    this.ws.send(JSON.stringify({ type: 'stop' }));
  }
}
