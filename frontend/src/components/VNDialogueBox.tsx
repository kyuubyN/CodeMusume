import React, { useState, useEffect, useRef, useCallback } from 'react';
import type { AvatarPose } from '../types';
import type { JapaneseSubtitleCue } from '../types/tts';
import {
  Volume2,
  VolumeX,
  Loader2,
  FastForward,
  Terminal,
  Radio,
  Send,
  MessageSquare,
  Sparkles,
  Activity,
} from 'lucide-react';
import { sounds } from '../services/audio';
import { ttsService } from '../services/tts';

interface Props {
  speakerName?: string;
  dialogue: string;
  pose: AvatarPose;
  onSendMessage: (msg: string) => void;
  isSending?: boolean;
  onOpenCommsLog: () => void;
  onSkip?: () => void;
}

export const VNDialogueBox: React.FC<Props> = ({
  speakerName = 'DR. AGNES TACHYON',
  dialogue,
  pose,
  onSendMessage,
  isSending = false,
  onOpenCommsLog,
  onSkip,
}) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [isTyping, setIsTyping] = useState(true);
  const [chatInput, setChatInput] = useState('');
  const [subtitleCue, setSubtitleCue] = useState<JapaneseSubtitleCue>(() =>
    ttsService.getSubtitleCue(pose, dialogue)
  );

  // References to manage concurrent playback and typewriter timers
  const typewriterTimerRef = useRef<number | null>(null);
  const isAudioDrivenRef = useRef(false);

  // Stop typewriter timer safely
  const clearTypewriterTimer = useCallback(() => {
    if (typewriterTimerRef.current !== null) {
      window.clearInterval(typewriterTimerRef.current);
      typewriterTimerRef.current = null;
    }
  }, []);

  // Update subtitle cue and reset text when dialogue or pose changes
  useEffect(() => {
    // Stop any active audio and unduck BGM
    ttsService.stopVoice();
    setIsPlayingAudio(false);
    setIsLoadingAudio(false);
    isAudioDrivenRef.current = false;
    clearTypewriterTimer();

    // Resolve matching Japanese subtitle cue for current mood/dialogue
    const cue = ttsService.getSubtitleCue(pose, dialogue);
    setSubtitleCue(cue);

    // Reset displayed text for new transmission
    setDisplayedText('');
    setIsTyping(true);

    if (!dialogue) {
      setIsTyping(false);
      return;
    }

    let index = 0;
    typewriterTimerRef.current = window.setInterval(() => {
      // If voice audio took over, pause the clock-based typewriter
      if (isAudioDrivenRef.current) return;

      index++;
      setDisplayedText(dialogue.slice(0, index));
      if (index >= dialogue.length) {
        clearTypewriterTimer();
        setIsTyping(false);
      }
    }, 18);

    return () => {
      clearTypewriterTimer();
      ttsService.stopVoice();
    };
  }, [dialogue, pose, clearTypewriterTimer]);

  // Dual-layer voice synthesis and synchronized playback
  const handleToggleVoice = async () => {
    if (isLoadingAudio) return;

    // If currently playing, clicking stops playback and unducks BGM
    if (isPlayingAudio) {
      ttsService.stopVoice();
      setIsPlayingAudio(false);
      isAudioDrivenRef.current = false;
      return;
    }

    if (!dialogue) return;

    setIsLoadingAudio(true);
    try {
      // Synthesize Japanese voice stream from Kokoro backend
      const response = await ttsService.synthesizeVoice(dialogue, pose);
      if (response.subtitleCue) {
        setSubtitleCue(response.subtitleCue);
      }

      if (response.audioBlob) {
        isAudioDrivenRef.current = true;
        setIsPlayingAudio(true);
        setIsTyping(true);

        await ttsService.playVoice(
          response.audioBlob,
          // Synchronize English text reveal with voice audio progress
          (progressRatio) => {
            const charCount = Math.min(
              dialogue.length,
              Math.max(1, Math.ceil(progressRatio * dialogue.length))
            );
            setDisplayedText(dialogue.slice(0, charCount));
          },
          // Callback when voice audio playback ends
          () => {
            setIsPlayingAudio(false);
            isAudioDrivenRef.current = false;
            setDisplayedText(dialogue);
            setIsTyping(false);
          }
        );
      }
    } catch (err) {
      console.warn('Dual-layer Japanese voice playback failed:', err);
      // Revert to standard typewriter completion on audio playback error
      isAudioDrivenRef.current = false;
      setDisplayedText(dialogue);
      setIsTyping(false);
    } finally {
      setIsLoadingAudio(false);
    }
  };

  // Instant text reveal and audio cancellation
  const handleInstantSkip = () => {
    clearTypewriterTimer();
    if (isPlayingAudio) {
      ttsService.stopVoice();
      setIsPlayingAudio(false);
    }
    isAudioDrivenRef.current = false;
    setDisplayedText(dialogue);
    setIsTyping(false);
    if (onSkip) {
      onSkip();
    }
  };

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!chatInput.trim() || isSending) return;
    sounds.playClick();
    onSendMessage(chatInput.trim());
    setChatInput('');
  };

  return (
    <div className="relative w-full max-w-5xl mx-auto px-6 pb-4 z-30 select-none font-mono">
      {/* Native Arknights Endfield Style Tactical Comms Box */}
      <div
        onClick={handleInstantSkip}
        className="relative w-full min-h-[180px] bg-[#0c0f16]/98 border border-white/15 rounded-tl-xl rounded-b-xl rounded-tr-3xl p-4 md:p-5 shadow-[0_20px_60px_rgba(0,0,0,0.9)] flex flex-col justify-between cursor-pointer group transition-colors"
      >
        {/* Top Industrial Yellow Accent Line */}
        <div className="absolute top-0 left-0 right-8 h-[2px] bg-gradient-to-r from-[#ffd000] via-[#ffd000]/60 to-transparent" />

        {/* Diagonal Tactical Cut Notch in Top Right */}
        <div className="absolute top-0 right-0 w-8 h-8 pointer-events-none border-t-2 border-r-2 border-[#ffd000]/80 rounded-tr-3xl" />

        {/* Top Header: Operator Callout & Frequency Telemetry */}
        <div className="flex items-center justify-between border-b border-white/10 pb-2.5">
          {/* Operator ID & Mini Avatar */}
          <div className="flex items-center gap-2.5">
            {/* Operator Mini Portrait */}
            <div className="w-9 h-9 rounded-lg overflow-hidden border border-[#ffd000]/60 bg-[#141822] shadow-sm flex-shrink-0 relative">
              <img
                src={`/avatars/${pose}.png`}
                alt={pose}
                className="w-full h-full object-cover object-top"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = '/avatars/idle.png';
                }}
              />
              {isPlayingAudio && (
                <div className="absolute inset-0 bg-[#00f0ff]/15 border border-[#00f0ff] animate-pulse rounded-lg pointer-events-none" />
              )}
            </div>

            {/* Operator Nameplate & Signal Telemetry */}
            <div className="flex flex-col">
              <div className="flex items-center gap-1.5">
                <span className="text-[11px] md:text-xs font-black tracking-widest text-[#ffd000] uppercase">
                  {speakerName}
                </span>
                <span className="text-[9px] text-[#7b8594] tracking-wider uppercase hidden sm:inline">
                  // CHIEF ARCHITECT [SSR]
                </span>
                <span className="text-[9px] px-1.5 py-0.2 rounded bg-[#ffd000]/10 text-[#ffd000] border border-[#ffd000]/30 font-bold uppercase">
                  {pose}
                </span>
              </div>
              <div className="flex items-center gap-2 text-[8px] tracking-widest text-[#7b8594]">
                <Radio className="w-2.5 h-2.5 text-[#00f0ff] animate-pulse" />
                <span>CH: 142.85 MHz // DEEPSEEK-V4.1 SYNAPSE</span>
                {isPlayingAudio && (
                  <span className="text-[#00f0ff] font-bold flex items-center gap-1 animate-pulse">
                    <Activity className="w-2.5 h-2.5" /> DUCKED 25%
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Comms History Log Button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onOpenCommsLog();
              }}
              title="Open Transmission History"
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-[#141824] hover:bg-[#1c2234] text-[#a0aec0] hover:text-[#00f0ff] border border-white/10 text-xs font-bold transition-all active:scale-95"
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">LOG // HISTORY</span>
            </button>

            {/* Dual-Layer Japanese Voice Synthesizer Button */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleToggleVoice();
              }}
              disabled={isLoadingAudio}
              title="Play Dr. Agnes authentic Japanese mad scientist voice (Kokoro-82M / jf_nezumi)"
              className={`flex items-center gap-1.5 px-3 py-1 rounded border shadow-md text-xs font-bold transition-all active:scale-95 ${
                isPlayingAudio
                  ? 'bg-[#00f0ff]/20 border-[#00f0ff] text-[#00f0ff] animate-pulse shadow-[0_0_12px_rgba(0,240,255,0.3)]'
                  : 'bg-[#161b26] hover:bg-[#202736] text-[#ffd000] border-[#ffd000]/40'
              }`}
            >
              {isLoadingAudio ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-[#ffd000]" />
              ) : isPlayingAudio ? (
                <VolumeX className="w-3.5 h-3.5 text-[#00f0ff]" />
              ) : (
                <Volume2 className="w-3.5 h-3.5 text-[#ffd000] animate-pulse" />
              )}
              <span className="tracking-wider">
                {isLoadingAudio
                  ? 'SYNTHESIZING...'
                  : isPlayingAudio
                  ? 'STOP // VOICE'
                  : 'VOICE // KOKORO JA'}
              </span>
            </button>
          </div>
        </div>

        {/* Dual-Layer Japanese Subtitle Cues & Romanized Voice Callout Banner */}
        <div className="my-2 px-3.5 py-1.5 rounded-lg bg-[#0e1422]/95 border border-[#00f0ff]/30 shadow-sm flex items-center justify-between gap-2 overflow-hidden">
          <div className="flex items-center gap-2 min-w-0">
            <Sparkles className="w-3.5 h-3.5 text-[#00f0ff] flex-shrink-0 animate-pulse" />
            <div className="flex items-center gap-2 truncate">
              {/* Authentically Localized Japanese Mad Scientist Cue */}
              <span className="text-xs md:text-sm font-bold text-[#e0f7ff] tracking-wide font-sans truncate drop-shadow">
                {subtitleCue.japanese}
              </span>
              {/* Romanized Voice Callout */}
              {subtitleCue.romaji && (
                <span className="text-[10px] text-[#7eb3d0] italic hidden md:inline truncate">
                  ({subtitleCue.romaji})
                </span>
              )}
            </div>
          </div>

          {/* Voice Mode Badge & Audio Ducking Indicator */}
          <div className="flex items-center gap-1.5 flex-shrink-0 text-[8px] md:text-[9px] font-bold">
            {isPlayingAudio ? (
              <span className="px-2 py-0.5 rounded bg-[#00f0ff]/20 text-[#00f0ff] border border-[#00f0ff]/50 flex items-center gap-1 animate-pulse">
                <span className="w-1.5 h-1.5 rounded-full bg-[#00f0ff] animate-ping" />
                AUDIO SYNC ACTIVE
              </span>
            ) : (
              <span className="px-1.5 py-0.5 rounded bg-white/5 text-[#7b8594] border border-white/10 hidden sm:inline">
                DUAL-LAYER JA
              </span>
            )}
          </div>
        </div>

        {/* Dialogue Text Body — High-contrast English Enterprise Architecture Text */}
        <div className="mb-2 min-h-[48px] md:min-h-[54px] flex items-start px-3.5 py-2.5 rounded-xl bg-[#121622]/90 border border-white/10 shadow-inner">
          <p className="text-sm md:text-base text-[#f0f3f6] leading-relaxed font-sans font-semibold tracking-wide">
            "{displayedText}"
            {/* Blinking Tactical Cursor */}
            {!isTyping && (
              <span className="inline-block ml-1 text-[#ffd000] font-mono animate-pulse">
                ■
              </span>
            )}
            {isTyping && (
              <span className="inline-block w-2 h-4 ml-1 bg-[#ffd000] animate-pulse align-middle" />
            )}
          </p>
        </div>

        {/* Direct Chat Transmission Input */}
        <form
          onSubmit={handleSend}
          onClick={(e) => e.stopPropagation()}
          className="flex items-center gap-2 pt-2 border-t border-white/10"
        >
          <div className="flex items-center gap-1 text-[9px] text-[#ffd000] font-mono tracking-widest flex-shrink-0">
            <Radio className="w-3 h-3 text-[#00f0ff] animate-pulse" />
            <span>TRANSMIT:</span>
          </div>
          <input
            type="text"
            value={chatInput}
            onChange={(e) => setChatInput(e.target.value)}
            disabled={isSending}
            placeholder="Transmit a question or converse directly with Dr. Agnes..."
            className="flex-1 bg-[#121620] border border-white/15 rounded-lg px-3 py-1.5 text-xs text-[#f0f3f6] font-mono focus:outline-none focus:border-[#ffd000] placeholder:text-[#556070] transition-colors"
          />
          <button
            type="submit"
            disabled={!chatInput.trim() || isSending}
            className="px-3.5 py-1.5 rounded-lg bg-[#ffd000] hover:bg-[#ffdb33] disabled:opacity-40 text-black font-mono font-black text-xs tracking-wider flex items-center gap-1 active:scale-95 transition-all shadow"
          >
            {isSending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-black" />
            ) : (
              <Send className="w-3.5 h-3.5 text-black" />
            )}
            <span>SEND</span>
          </button>
        </form>

        {/* Bottom Status Info */}
        <div className="flex items-center justify-between text-[9px] tracking-widest text-[#7b8594] pt-1">
          <div className="flex items-center gap-1.5 opacity-70">
            <Terminal className="w-2.5 h-2.5 text-[#00f0ff]" />
            <span>DEEPSEEK-V4.1 // REAL-TIME REASONING ACTIVE</span>
          </div>

          <button
            onClick={(e) => {
              e.stopPropagation();
              handleInstantSkip();
            }}
            className="hover:text-[#ffd000] flex items-center gap-1 transition-colors uppercase font-bold"
          >
            <FastForward className="w-2.5 h-2.5" />
            <span>ADVANCE TEXT</span>
          </button>
        </div>
      </div>
    </div>
  );
};
