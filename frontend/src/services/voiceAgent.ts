/**
 * AssemblyAI Voice Agent API client (browser side).
 *
 * One WebSocket carries everything: mic audio up (PCM16 @ 24 kHz, base64),
 * Agnes's voice down, live transcripts, turn detection and tool calls.
 * Spec: https://www.assemblyai.com/docs/voice-agents/voice-agent-api
 */
import { audioService } from './audio';

const WS_URL = 'wss://agents.assemblyai.com/v1/ws';
const RATE = 24000;

export type VoiceStatus =
  | 'idle'
  | 'connecting'
  | 'listening'
  | 'user_speaking'
  | 'thinking'
  | 'speaking'
  | 'error';

export interface ToolCall {
  callId: string;
  name: string;
  args: Record<string, unknown>;
}

export interface VoiceAgentHandlers {
  onStatus(status: VoiceStatus): void;
  onUserPartial(text: string): void;
  onUserFinal(text: string): void;
  onAgentText(text: string, interrupted: boolean): void;
  onToolCall(call: ToolCall): Promise<unknown>;
  onError(message: string): void;
  onEnded(): void;
}

export interface VoiceSessionSource {
  getToken(): Promise<string>;
  getSession(): Promise<Record<string, unknown>>;
}

// Captures mic audio at the context's native rate, resamples to 24 kHz with
// linear interpolation, and posts ~50 ms PCM16 chunks plus an RMS level.
// Resampling here (instead of forcing AudioContext({sampleRate: 24000}))
// keeps echo cancellation working in Firefox and Safari.
const CAPTURE_WORKLET = `
class PcmCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.step = sampleRate / ${RATE};
    this.pos = 0;
    this.prev = 0;
    this.out = new Int16Array(${RATE / 20});
    this.n = 0;
    this.sumSq = 0;
  }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch || ch.length === 0) return true;
    const len = ch.length;
    let pos = this.pos;
    while (pos < len - 1) {
      const i = Math.floor(pos);
      const f = pos - i;
      const a = i < 0 ? this.prev : ch[i];
      const s = a + (ch[i + 1] - a) * f;
      this.sumSq += s * s;
      this.out[this.n++] = Math.max(-32768, Math.min(32767, Math.round(s * 32767)));
      if (this.n === this.out.length) {
        const level = Math.sqrt(this.sumSq / this.n);
        const buf = this.out.buffer;
        this.port.postMessage({ pcm: buf, level }, [buf]);
        this.out = new Int16Array(${RATE / 20});
        this.n = 0;
        this.sumSq = 0;
      }
      pos += this.step;
    }
    this.pos = pos - len;
    this.prev = ch[len - 1];
    return true;
  }
}
registerProcessor('pcm-capture', PcmCapture);
`;

function toBase64(bytes: Uint8Array): string {
  let bin = '';
  for (let i = 0; i < bytes.length; i += 0x8000) {
    bin += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + 0x8000)));
  }
  return btoa(bin);
}

function pcm16Base64ToFloat32(b64: string): Float32Array {
  const bin = atob(b64);
  const samples = new Float32Array(bin.length >> 1);
  for (let i = 0; i < samples.length; i++) {
    let v = bin.charCodeAt(i * 2) | (bin.charCodeAt(i * 2 + 1) << 8);
    if (v >= 0x8000) v -= 0x10000;
    samples[i] = v / 32768;
  }
  return samples;
}

export class VoiceAgent {
  private ws: WebSocket | null = null;
  private ctx: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private worklet: AudioWorkletNode | null = null;
  private analyser: AnalyserNode | null = null;
  private outGain: GainNode | null = null;
  private sources = new Set<AudioBufferSourceNode>();
  private playhead = 0;
  private ready = false;
  private replyActive = false;
  private pendingResults: { call_id: string; result: string }[] = [];
  private status: VoiceStatus = 'idle';
  private ducked = false;
  private micLevel = 0;
  private levelBuf: Float32Array | null = null;
  muted = false;

  constructor(private source: VoiceSessionSource, private h: VoiceAgentHandlers) {}

  get isLive(): boolean {
    return this.ready && this.ws?.readyState === WebSocket.OPEN;
  }

  /** Analyser on Agnes's voice output — used for lip sync / avatar motion. */
  get outputAnalyser(): AnalyserNode | null {
    return this.analyser;
  }

  /** RMS of Agnes's voice right now, 0..1. */
  getOutputLevel(): number {
    if (!this.analyser) return 0;
    if (!this.levelBuf || this.levelBuf.length !== this.analyser.fftSize) {
      this.levelBuf = new Float32Array(this.analyser.fftSize);
    }
    this.analyser.getFloatTimeDomainData(this.levelBuf as Float32Array<ArrayBuffer>);
    let sum = 0;
    for (let i = 0; i < this.levelBuf.length; i++) sum += this.levelBuf[i] * this.levelBuf[i];
    return Math.min(1, Math.sqrt(sum / this.levelBuf.length) * 4);
  }

  /** RMS of the trainer's microphone, 0..1. */
  getInputLevel(): number {
    return this.muted ? 0 : Math.min(1, this.micLevel * 6);
  }

  async start(): Promise<void> {
    if (this.ws) return;
    this.setStatus('connecting');
    try {
      // Mic + audio graph first: both need the click's user activation.
      this.ctx = new AudioContext();
      await this.ctx.resume();
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
      });
      const blobUrl = URL.createObjectURL(new Blob([CAPTURE_WORKLET], { type: 'application/javascript' }));
      await this.ctx.audioWorklet.addModule(blobUrl);
      URL.revokeObjectURL(blobUrl);

      this.outGain = this.ctx.createGain();
      this.analyser = this.ctx.createAnalyser();
      this.analyser.fftSize = 1024;
      this.analyser.smoothingTimeConstant = 0.5;
      this.outGain.connect(this.analyser).connect(this.ctx.destination);

      const mic = this.ctx.createMediaStreamSource(this.stream);
      this.worklet = new AudioWorkletNode(this.ctx, 'pcm-capture');
      this.worklet.port.onmessage = (e: MessageEvent<{ pcm: ArrayBuffer; level: number }>) => {
        this.micLevel = e.data.level;
        if (!this.isLive || this.muted) return;
        this.send({ type: 'input.audio', audio: toBase64(new Uint8Array(e.data.pcm)) });
      };
      // The worklet must be pulled by the graph to run; route it into a muted gain.
      const sink = this.ctx.createGain();
      sink.gain.value = 0;
      mic.connect(this.worklet).connect(sink).connect(this.ctx.destination);

      const [token, session] = await Promise.all([this.source.getToken(), this.source.getSession()]);
      const url = new URL(WS_URL);
      url.searchParams.set('token', token);
      this.ws = new WebSocket(url);
      this.ws.onopen = () => this.send({ type: 'session.update', session });
      this.ws.onmessage = (ev) => this.onMessage(JSON.parse(ev.data));
      this.ws.onerror = () => this.h.onError('Voice connection error.');
      this.ws.onclose = () => this.teardown();
    } catch (err) {
      const msg =
        err instanceof DOMException && err.name === 'NotAllowedError'
          ? 'Microphone permission denied.'
          : err instanceof Error
            ? err.message
            : String(err);
      this.h.onError(msg);
      this.teardown('error');
    }
  }

  stop(): void {
    if (this.ws?.readyState === WebSocket.OPEN) this.send({ type: 'session.end' });
    this.ws?.close();
    this.teardown();
  }

  setMuted(muted: boolean): void {
    this.muted = muted;
  }

  /** Text the trainer typed instead of saying. */
  sendText(text: string): void {
    this.send({
      type: 'reply.create',
      instructions: `[TRAINER TYPED] "${text}". Respond as if they had said it out loud, calling tools if needed.`,
    });
  }

  /** Something happened on screen that Agnes should react to. */
  notify(event: string): void {
    this.send({ type: 'reply.create', instructions: `[GAME EVENT] ${event}` });
  }

  updateSystemPrompt(systemPrompt: string): void {
    this.send({ type: 'session.update', session: { system_prompt: systemPrompt } });
  }

  // ------------------------------------------------------------------

  private send(msg: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) this.ws.send(JSON.stringify(msg));
  }

  private setStatus(s: VoiceStatus): void {
    if (s === this.status) return;
    this.status = s;
    const speaking = s === 'speaking';
    if (speaking && !this.ducked) {
      audioService.duckBGM(0.2);
      this.ducked = true;
    } else if (!speaking && this.ducked) {
      audioService.unduckBGM();
      this.ducked = false;
    }
    this.h.onStatus(s);
  }

  private onMessage(msg: Record<string, any>): void {
    switch (msg.type) {
      case 'session.ready':
        this.ready = true;
        this.setStatus('listening');
        break;
      case 'input.speech.started':
        // Barge-in: cut Agnes off locally right away; the server stops generating.
        this.flushPlayback();
        this.setStatus('user_speaking');
        break;
      case 'input.speech.stopped':
        this.setStatus('thinking');
        break;
      case 'transcript.user.delta':
        this.h.onUserPartial(msg.text ?? '');
        break;
      case 'transcript.user':
        this.h.onUserPartial('');
        this.h.onUserFinal(msg.text ?? '');
        break;
      case 'reply.started':
        this.replyActive = true;
        if (this.status !== 'speaking') this.setStatus('thinking');
        break;
      case 'reply.audio':
        this.play(msg.data);
        break;
      case 'transcript.agent':
        this.h.onAgentText(msg.text ?? '', Boolean(msg.interrupted));
        break;
      case 'reply.done':
        this.replyActive = false;
        if (msg.status === 'interrupted') this.flushPlayback();
        this.flushToolResults();
        if (this.sources.size === 0 && this.status !== 'user_speaking') this.setStatus('listening');
        break;
      case 'tool.call':
        this.runTool({ callId: msg.call_id, name: msg.name, args: msg.arguments ?? {} });
        break;
      case 'session.error':
      case 'error':
        this.h.onError(msg.message || msg.code || 'Voice agent error');
        break;
      case 'session.ended':
        this.ws?.close();
        break;
    }
  }

  private async runTool(call: ToolCall): Promise<void> {
    this.setStatus('thinking');
    let result: unknown;
    try {
      result = await this.h.onToolCall(call);
    } catch (err) {
      result = { error: err instanceof Error ? err.message : String(err) };
    }
    this.pendingResults.push({ call_id: call.callId, result: JSON.stringify(result ?? {}) });
    // Results go out after the reply that announced the tool finishes.
    if (!this.replyActive) this.flushToolResults();
  }

  private flushToolResults(): void {
    for (const r of this.pendingResults.splice(0)) this.send({ type: 'tool.result', ...r });
  }

  private play(b64: string): void {
    if (!this.ctx || !this.outGain) return;
    const samples = pcm16Base64ToFloat32(b64);
    if (samples.length === 0) return;
    const buffer = this.ctx.createBuffer(1, samples.length, RATE);
    buffer.getChannelData(0).set(samples);
    const src = this.ctx.createBufferSource();
    src.buffer = buffer;
    src.connect(this.outGain);
    const now = this.ctx.currentTime;
    this.playhead = Math.max(this.playhead, now + 0.03);
    src.start(this.playhead);
    this.playhead += buffer.duration;
    this.sources.add(src);
    src.onended = () => {
      this.sources.delete(src);
      if (this.sources.size === 0 && !this.replyActive && this.status === 'speaking') {
        this.setStatus('listening');
      }
    };
    this.setStatus('speaking');
  }

  private flushPlayback(): void {
    for (const s of this.sources) {
      s.onended = null;
      try {
        s.stop();
      } catch {
        /* already stopped */
      }
    }
    this.sources.clear();
    this.playhead = this.ctx?.currentTime ?? 0;
  }

  private teardown(finalStatus: VoiceStatus = 'idle'): void {
    const wasActive = this.ws !== null || this.ctx !== null;
    this.flushPlayback();
    this.ready = false;
    this.replyActive = false;
    this.pendingResults = [];
    this.worklet?.port.close();
    this.stream?.getTracks().forEach((t) => t.stop());
    this.ctx?.close().catch(() => undefined);
    if (this.ws) {
      this.ws.onclose = null;
      this.ws.onmessage = null;
    }
    this.ws = null;
    this.ctx = null;
    this.stream = null;
    this.worklet = null;
    this.analyser = null;
    this.outGain = null;
    this.micLevel = 0;
    this.setStatus(finalStatus);
    if (wasActive) this.h.onEnded();
  }
}
