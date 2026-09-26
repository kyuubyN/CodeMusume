export interface AudioService {
  playBGM(trackPath?: string): void;
  pauseBGM(): void;
  resumeBGM(): void;
  setBGMVolume(volume: number): void; // 0.0 - 1.0
  getBGMVolume(): number;
  toggleMute(): boolean;
  isMuted(): boolean;
  duckBGM(duckRatio?: number): void; // ducks to 0.2 - 0.3
  unduckBGM(): void; // restores original volume
}

const STORAGE_KEY_VOLUME = 'codemusume_bgm_volume';
const STORAGE_KEY_MUTED = 'codemusume_bgm_muted';
export const DEFAULT_BGM_TRACK = '/assets/soundtrack/Steady Steps.mp3';

export class AudioManager implements AudioService {
  private bgmAudio: HTMLAudioElement | null = null;
  private currentTrackPath: string = DEFAULT_BGM_TRACK;
  private userVolume: number = 0.6;
  private muted: boolean = false;
  private duckCount: number = 0;
  private duckRatio: number = 0.25; // Default duck to 25% (in 20-30% range)
  private shouldPlay: boolean = false;
  private listeners: Set<() => void> = new Set();
  private fadeInterval: number | null = null;
  private unlockListenerAttached: boolean = false;

  constructor() {
    this.loadSettings();
    if (typeof window !== 'undefined') {
      this.initAudio();
    }
  }

  private loadSettings(): void {
    if (typeof window === 'undefined' || typeof localStorage === 'undefined') return;
    try {
      const savedVol = localStorage.getItem(STORAGE_KEY_VOLUME);
      if (savedVol !== null) {
        const parsed = parseFloat(savedVol);
        if (!isNaN(parsed) && parsed >= 0 && parsed <= 1) {
          this.userVolume = parsed;
        }
      }
      const savedMuted = localStorage.getItem(STORAGE_KEY_MUTED);
      if (savedMuted !== null) {
        this.muted = savedMuted === 'true';
      }
    } catch (e) {
      console.warn('Failed to load audio settings from localStorage:', e);
    }
  }

  private saveSettings(): void {
    if (typeof window === 'undefined' || typeof localStorage === 'undefined') return;
    try {
      localStorage.setItem(STORAGE_KEY_VOLUME, this.userVolume.toString());
      localStorage.setItem(STORAGE_KEY_MUTED, this.muted.toString());
    } catch (e) {
      console.warn('Failed to save audio settings to localStorage:', e);
    }
  }

  private initAudio(): void {
    if (typeof window === 'undefined' || typeof Audio === 'undefined') return;
    if (!this.bgmAudio) {
      this.bgmAudio = new Audio(this.currentTrackPath);
      this.bgmAudio.loop = true;
      this.bgmAudio.preload = 'auto';
      this.applyEffectiveVolume(false);
    }
  }

  public subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private notifyListeners(): void {
    this.listeners.forEach((listener) => {
      try {
        listener();
      } catch (e) {
        console.error('Error in audio listener:', e);
      }
    });
  }

  private getEffectiveVolume(): number {
    if (this.muted) return 0;
    if (this.duckCount > 0) {
      return Math.max(0, Math.min(1, this.userVolume * this.duckRatio));
    }
    return Math.max(0, Math.min(1, this.userVolume));
  }

  private applyEffectiveVolume(smooth: boolean = false): void {
    const target = this.getEffectiveVolume();
    if (!this.bgmAudio) return;

    if (!smooth || typeof window === 'undefined') {
      if (this.fadeInterval !== null) {
        window.clearInterval(this.fadeInterval);
        this.fadeInterval = null;
      }
      this.bgmAudio.volume = target;
      return;
    }

    // Smooth volume fade ramp (approx 200ms)
    if (this.fadeInterval !== null) {
      window.clearInterval(this.fadeInterval);
      this.fadeInterval = null;
    }

    const startVolume = this.bgmAudio.volume;
    if (Math.abs(startVolume - target) < 0.01) {
      this.bgmAudio.volume = target;
      return;
    }

    const durationMs = 200;
    const steps = 10;
    const stepDuration = durationMs / steps;
    let step = 0;

    this.fadeInterval = window.setInterval(() => {
      step++;
      const factor = step / steps;
      const current = startVolume + (target - startVolume) * factor;
      if (this.bgmAudio) {
        this.bgmAudio.volume = Math.max(0, Math.min(1, current));
      }
      if (step >= steps) {
        if (this.fadeInterval !== null) {
          window.clearInterval(this.fadeInterval);
          this.fadeInterval = null;
        }
        if (this.bgmAudio) {
          this.bgmAudio.volume = target;
        }
      }
    }, stepDuration);
  }

  private attachUnlockListener(): void {
    if (this.unlockListenerAttached || typeof window === 'undefined') return;
    this.unlockListenerAttached = true;

    const unlock = () => {
      if (this.shouldPlay && this.bgmAudio && this.bgmAudio.paused) {
        this.bgmAudio.play().catch((err) => {
          console.warn('Audio unlock playback failed:', err);
        });
      }
      this.unlockListenerAttached = false;
      window.removeEventListener('pointerdown', unlock);
      window.removeEventListener('keydown', unlock);
      window.removeEventListener('click', unlock);
    };

    window.addEventListener('pointerdown', unlock, { once: true, passive: true });
    window.addEventListener('keydown', unlock, { once: true, passive: true });
    window.addEventListener('click', unlock, { once: true, passive: true });
  }

  playBGM(trackPath?: string): void {
    const targetTrack = trackPath || this.currentTrackPath || DEFAULT_BGM_TRACK;
    this.shouldPlay = true;

    if (typeof window === 'undefined' || typeof Audio === 'undefined') return;
    this.initAudio();
    if (!this.bgmAudio) return;

    if (this.currentTrackPath !== targetTrack) {
      this.currentTrackPath = targetTrack;
      this.bgmAudio.src = targetTrack;
      this.bgmAudio.currentTime = 0;
    }

    this.applyEffectiveVolume(false);

    if (!this.bgmAudio.paused) {
      return;
    }

    const playPromise = this.bgmAudio.play();
    if (playPromise !== undefined) {
      playPromise.catch((err) => {
        console.warn('BGM play deferred until user interaction:', err?.message || err);
        this.attachUnlockListener();
      });
    }
  }

  pauseBGM(): void {
    this.shouldPlay = false;
    if (this.bgmAudio && !this.bgmAudio.paused) {
      this.bgmAudio.pause();
    }
    this.notifyListeners();
  }

  resumeBGM(): void {
    this.shouldPlay = true;
    if (this.bgmAudio) {
      if (this.bgmAudio.paused) {
        this.bgmAudio.play().catch((err) => {
          console.warn('BGM resume deferred until user interaction:', err);
          this.attachUnlockListener();
        });
      }
    } else {
      this.playBGM();
    }
    this.notifyListeners();
  }

  setBGMVolume(volume: number): void {
    const clamped = Math.max(0, Math.min(1, Number(volume) || 0));
    this.userVolume = clamped;
    if (this.muted && clamped > 0) {
      this.muted = false;
    }
    this.saveSettings();
    this.applyEffectiveVolume(false);
    this.notifyListeners();
  }

  getBGMVolume(): number {
    return this.userVolume;
  }

  toggleMute(): boolean {
    this.muted = !this.muted;
    this.saveSettings();
    this.applyEffectiveVolume(false);
    this.notifyListeners();
    return this.muted;
  }

  isMuted(): boolean {
    return this.muted;
  }

  duckBGM(duckRatio: number = 0.25): void {
    if (duckRatio >= 0 && duckRatio <= 1) {
      this.duckRatio = duckRatio;
    }
    this.duckCount++;
    this.applyEffectiveVolume(true);
  }

  unduckBGM(): void {
    this.duckCount = Math.max(0, this.duckCount - 1);
    this.applyEffectiveVolume(true);
  }
}

export const audioService = new AudioManager();

class SoundController {
  private ctx: AudioContext | null = null;
  private currentAudio: HTMLAudioElement | null = null;

  private getContext(): AudioContext {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      this.ctx = new AudioCtx();
    }
    if (this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
    return this.ctx;
  }

  // Play voice speech audio blob from Kokoro-82M TTS with automatic BGM ducking
  async playVoice(blob: Blob): Promise<void> {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
      audioService.unduckBGM();
    }
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    this.currentAudio = audio;

    // Automatic BGM ducking while speech is playing
    audioService.duckBGM();

    let cleanedUp = false;
    const cleanup = () => {
      if (cleanedUp) return;
      cleanedUp = true;
      URL.revokeObjectURL(url);
      audioService.unduckBGM();
      if (this.currentAudio === audio) {
        this.currentAudio = null;
      }
    };

    audio.onended = cleanup;
    audio.onerror = cleanup;
    audio.onpause = () => {
      if (audio.currentTime === 0 || audio.ended) {
        cleanup();
      }
    };

    try {
      await audio.play();
    } catch {
      cleanup();
    }
  }

  // Synthesized Arcade Sound Effects using Web Audio API
  playClick(): void {
    try {
      const ctx = this.getContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(800, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(400, ctx.currentTime + 0.08);

      gain.gain.setValueAtTime(0.15, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.08);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.08);
    } catch {
      // AudioContext not allowed yet
    }
  }

  playSuccess(): void {
    try {
      const ctx = this.getContext();
      const notes = [523.25, 659.25, 783.99, 1046.50]; // C5, E5, G5, C6 (Fanfare)
      notes.forEach((freq, idx) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();

        const startTime = ctx.currentTime + idx * 0.09;
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(freq, startTime);

        gain.gain.setValueAtTime(0.2, startTime);
        gain.gain.exponentialRampToValueAtTime(0.01, startTime + 0.25);

        osc.connect(gain);
        gain.connect(ctx.destination);

        osc.start(startTime);
        osc.stop(startTime + 0.25);
      });
    } catch {
      // AudioContext not allowed yet
    }
  }

  playFailure(): void {
    try {
      const ctx = this.getContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(320, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(140, ctx.currentTime + 0.35);

      gain.gain.setValueAtTime(0.2, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.35);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.35);
    } catch {
      // AudioContext not allowed yet
    }
  }

  playSkill(): void {
    try {
      const ctx = this.getContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(440, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(1320, ctx.currentTime + 0.2);

      gain.gain.setValueAtTime(0.25, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.4);
    } catch {
      // AudioContext not allowed yet
    }
  }

  playRaceStart(): void {
    try {
      const ctx = this.getContext();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(1800, ctx.currentTime);
      osc.frequency.setValueAtTime(2400, ctx.currentTime + 0.1);

      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.4);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.4);
    } catch {
      // AudioContext not allowed yet
    }
  }

  // Delegation methods to audioService
  playBGM(trackPath?: string): void {
    audioService.playBGM(trackPath);
  }
  pauseBGM(): void {
    audioService.pauseBGM();
  }
  resumeBGM(): void {
    audioService.resumeBGM();
  }
  setBGMVolume(volume: number): void {
    audioService.setBGMVolume(volume);
  }
  getBGMVolume(): number {
    return audioService.getBGMVolume();
  }
  toggleMute(): boolean {
    return audioService.toggleMute();
  }
  isMuted(): boolean {
    return audioService.isMuted();
  }
  duckBGM(duckRatio?: number): void {
    audioService.duckBGM(duckRatio);
  }
  unduckBGM(): void {
    audioService.unduckBGM();
  }
}

export const sounds = new SoundController();
export default audioService;

