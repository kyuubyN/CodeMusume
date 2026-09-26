import React, { useState, useEffect } from 'react';
import { AvatarPose } from '../types';
import { Volume2, Loader2 } from 'lucide-react';
import { api } from '../services/api';
import { sounds } from '../services/audio';

interface Props {
  speakerName?: string;
  dialogue: string;
  pose: AvatarPose;
}

export const DialogueBox: React.FC<Props> = ({
  speakerName = 'Dr. Agnes Tachyon',
  dialogue,
  pose,
}) => {
  const [displayedText, setDisplayedText] = useState('');
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  // Typewriter effect
  useEffect(() => {
    let index = 0;
    setDisplayedText('');
    const timer = setInterval(() => {
      index++;
      setDisplayedText(dialogue.slice(0, index));
      if (index >= dialogue.length) {
        clearInterval(timer);
      }
    }, 18);

    return () => clearInterval(timer);
  }, [dialogue]);

  // Voice speech synthesis trigger
  const handlePlayVoice = async () => {
    if (isPlayingAudio || !dialogue) return;
    setIsPlayingAudio(true);
    try {
      const audioBlob = await api.synthesizeAudio(dialogue);
      if (audioBlob) {
        await sounds.playVoice(audioBlob);
      }
    } catch {
      // Speech failed silently
    } finally {
      setIsPlayingAudio(false);
    }
  };

  return (
    <div className="w-full px-3 pb-3 pt-1">
      <div className="relative bg-slate-900/95 border-2 border-slate-700/90 rounded-2xl p-3 shadow-2xl backdrop-blur-md flex items-start gap-3">
        {/* Agnes Avatar Portrait */}
        <div className="relative flex-shrink-0 w-12 h-12 rounded-xl overflow-hidden border-2 border-cyan-400/80 bg-slate-950 shadow-md">
          <img
            src={`/avatars/${pose}.png`}
            alt={pose}
            className="w-full h-full object-cover object-top"
            onError={(e) => {
              (e.target as HTMLImageElement).src = '/avatars/idle.png';
            }}
          />
        </div>

        {/* Text Area */}
        <div className="flex-1 min-w-0 flex flex-col gap-0.5">
          {/* Speaker Header with Audio Button */}
          <div className="flex items-center justify-between">
            <span className="text-xs font-black text-cyan-300 tracking-wider">
              {speakerName}
            </span>

            {/* TTS Voice Play Button */}
            <button
              onClick={handlePlayVoice}
              disabled={isPlayingAudio}
              title="Ouvir voz sintetizada da Agnes (Kokoro-82M)"
              className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-800 hover:bg-slate-700 border border-slate-600 text-[10px] text-slate-300 font-bold transition-all active:scale-90"
            >
              {isPlayingAudio ? (
                <Loader2 className="w-3 h-3 animate-spin text-cyan-400" />
              ) : (
                <Volume2 className="w-3 h-3 text-cyan-400" />
              )}
              <span>Voz</span>
            </button>
          </div>

          {/* Dialogue Text */}
          <p className="text-xs font-semibold text-slate-100 leading-relaxed min-h-[38px]">
            {displayedText}
            {displayedText.length < dialogue.length && (
              <span className="inline-block w-1.5 h-3 ml-0.5 bg-cyan-400 animate-pulse" />
            )}
          </p>
        </div>
      </div>
    </div>
  );
};
