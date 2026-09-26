import type { AvatarPose } from '../types';
import {
  type JapaneseSubtitleCue,
  type TTSVoiceRequest,
  type TTSVoiceResponse,
  resolveTachyonSubtitleCue,
} from '../types/tts';
import { audioService } from './audio';

const API_BASE = '/api';

/**
 * Progress callback for audio-to-text timing synchronization
 */
export type VoiceProgressCallback = (progressRatio: number, currentTime: number, duration: number) => void;

/**
 * Service managing dual-layer Kokoro Japanese voice synthesis,
 * synchronized audio playback, BGM ducking, and subtitle cues.
 */
export class TTSService {
  private currentAudio: HTMLAudioElement | null = null;
  private currentBlobUrl: string | null = null;
  private isDucked: boolean = false;
  private activeProgressCallback: VoiceProgressCallback | null = null;
  private onEndCallbacks: Set<() => void> = new Set();

  /**
   * Request Japanese synthesized audio and subtitle cues from the backend.
   * Tries /api/tts/generate first, falling back to /api/audio/synthesize.
   */
  async synthesizeVoice(
    text: string,
    mood: AvatarPose = 'idle'
  ): Promise<TTSVoiceResponse> {
    const subtitleCue = resolveTachyonSubtitleCue(mood, text);

    if (!text.trim()) {
      return { audioBlob: null, subtitleCue };
    }

    const payload: TTSVoiceRequest = {
      text,
      mood,
      voice: 'jf_nezumi',
      speed: 1.04,
      language: 'ja',
    };

    // 1. Try dedicated Tachyon TTS endpoint /api/tts/generate
    try {
      const res = await fetch(`${API_BASE}/tts/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (res.ok && res.status !== 204) {
        const contentType = res.headers.get('content-type') || '';
        const headerCue = res.headers.get('x-subtitle-cue');
        const headerJp = res.headers.get('x-japanese-text');
        const headerRomaji = res.headers.get('x-romanized-callout');

        let dynamicCue = subtitleCue;
        if (headerCue) {
          dynamicCue = {
            ...subtitleCue,
            japanese: headerCue,
            romaji: headerRomaji || subtitleCue.romaji,
          };
        }

        if (contentType.includes('application/json')) {
          const data = await res.json();
          let blob: Blob | null = null;
          if (data.audio_base64) {
            const binary = atob(data.audio_base64);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
              bytes[i] = binary.charCodeAt(i);
            }
            blob = new Blob([bytes], { type: 'audio/mpeg' });
          } else if (data.audio_url) {
            const audioRes = await fetch(data.audio_url);
            if (audioRes.ok) blob = await audioRes.blob();
          }

          if (data.subtitle_cue) {
            dynamicCue = {
              ...subtitleCue,
              japanese: data.subtitle_cue,
              romaji: data.romanized_callout || data.romaji || subtitleCue.romaji,
              englishCallout: data.english_callout || subtitleCue.englishCallout,
            };
          }

          return {
            audioBlob: blob,
            subtitleCue: dynamicCue,
            japaneseSpeechText: data.japanese_speech_text || headerJp || undefined,
          };
        }

        const audioBlob = await res.blob();
        return {
          audioBlob: audioBlob.size > 0 ? audioBlob : null,
          subtitleCue: dynamicCue,
          japaneseSpeechText: headerJp || undefined,
        };
      }
    } catch (err) {
      console.warn('Endpoint /api/tts/generate unreachable, falling back to /api/audio/synthesize:', err);
    }

    // 2. Fallback to /api/audio/synthesize
    try {
      const res = await fetch(`${API_BASE}/audio/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text,
          voice: 'jf_nezumi',
          speed: 1.04,
        }),
      });

      if (res.ok && res.status !== 204) {
        const blob = await res.blob();
        return {
          audioBlob: blob.size > 0 ? blob : null,
          subtitleCue,
        };
      }
    } catch (err) {
      console.warn('Fallback synthesis failed:', err);
    }

    return { audioBlob: null, subtitleCue };
  }

  /**
   * Play speech audio blob with synchronized BGM ducking and time-update telemetry.
   */
  async playVoice(
    audioBlob: Blob,
    onProgress?: VoiceProgressCallback,
    onEnded?: () => void
  ): Promise<void> {
    this.stopVoice();

    this.activeProgressCallback = onProgress || null;
    if (onEnded) {
      this.onEndCallbacks.add(onEnded);
    }

    const url = URL.createObjectURL(audioBlob);
    this.currentBlobUrl = url;
    const audio = new Audio(url);
    this.currentAudio = audio;

    // Apply audio ducking to 25% volume as specified in R2/R3 requirements
    this.duck();

    const cleanup = () => {
      this.unduck();
      if (this.currentBlobUrl) {
        URL.revokeObjectURL(this.currentBlobUrl);
        this.currentBlobUrl = null;
      }
      if (this.currentAudio === audio) {
        this.currentAudio = null;
      }
      this.activeProgressCallback = null;

      // Trigger and clear callbacks
      const callbacks = Array.from(this.onEndCallbacks);
      this.onEndCallbacks.clear();
      callbacks.forEach((cb) => {
        try {
          cb();
        } catch (e) {
          console.error('Error in voice onEnd callback:', e);
        }
      });
    };

    audio.ontimeupdate = () => {
      if (this.activeProgressCallback && audio.duration && !isNaN(audio.duration)) {
        const ratio = Math.max(0, Math.min(1, audio.currentTime / audio.duration));
        this.activeProgressCallback(ratio, audio.currentTime, audio.duration);
      }
    };

    audio.onended = cleanup;
    audio.onerror = (e) => {
      console.warn('Voice playback error:', e);
      cleanup();
    };

    audio.onpause = () => {
      // If paused due to reaching end or interruption
      if (audio.ended || audio.currentTime === 0) {
        cleanup();
      }
    };

    try {
      await audio.play();
    } catch (err) {
      console.warn('Audio play restricted or aborted:', err);
      cleanup();
      throw err;
    }
  }

  /**
   * Immediately stops voice playback, unducks BGM, and cleans up resources.
   */
  stopVoice(): void {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.currentAudio = null;
    }

    if (this.currentBlobUrl) {
      URL.revokeObjectURL(this.currentBlobUrl);
      this.currentBlobUrl = null;
    }

    this.unduck();
    this.activeProgressCallback = null;

    const callbacks = Array.from(this.onEndCallbacks);
    this.onEndCallbacks.clear();
    callbacks.forEach((cb) => {
      try {
        cb();
      } catch (e) {
        console.error('Error executing voice end callback:', e);
      }
    });
  }

  /**
   * Resolve Japanese subtitle cue for a given mood/pose and dialogue text.
   */
  getSubtitleCue(mood: AvatarPose = 'idle', text?: string): JapaneseSubtitleCue {
    return resolveTachyonSubtitleCue(mood, text);
  }

  /**
   * Returns whether voice playback is currently active.
   */
  isPlaying(): boolean {
    return this.currentAudio !== null && !this.currentAudio.paused;
  }

  /**
   * Duck BGM to 25% volume (0.25). Ensures only one active duck at a time.
   */
  private duck(): void {
    if (!this.isDucked) {
      this.isDucked = true;
      audioService.duckBGM(0.25);
    }
  }

  /**
   * Restore original BGM volume.
   */
  private unduck(): void {
    if (this.isDucked) {
      this.isDucked = false;
      audioService.unduckBGM();
    }
  }
}

export const ttsService = new TTSService();
export default ttsService;
