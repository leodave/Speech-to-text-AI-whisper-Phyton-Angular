import { Component, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranscriptService } from './transcript.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements OnDestroy {
  recording = false;
  mediaRecorder?: MediaRecorder;

  partialText = '';
  finalText = '';
  language: string | undefined = 'en';

  subs: Subscription[] = [];

  constructor(private svc: TranscriptService) {
    this.subs.push(this.svc.partial$.subscribe((t) => (this.partialText = t)));
    this.subs.push(this.svc.final$.subscribe((t) => (this.finalText = t)));
  }

  async start() {
    if (this.recording) return;

    // 1) Connect to backend WS
    this.svc.connect(this.language);

    // 2) Get mic stream
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : (MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '');

    this.mediaRecorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);

    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) this.svc.sendAudioChunk(e.data);
    };

    this.mediaRecorder.start(250);
    this.recording = true;
    this.finalText = '';
    this.partialText = '';
  }

  stop() {
    if (!this.recording) return;
    this.mediaRecorder?.stop();
    this.svc.stop();
    this.recording = false;
  }

  ngOnDestroy() {
    this.subs.forEach((s) => s.unsubscribe());
    if (this.recording) {
      this.mediaRecorder?.stop();
      this.svc.stop();
    }
  }
}
