import { AvatarPose } from './index';

/**
 * Agnes Tachyon Japanese Subtitle Cue and Vocal Delivery Metadata
 */
export interface JapaneseSubtitleCue {
  japanese: string;
  romaji: string;
  englishCallout: string;
  mood: AvatarPose;
  audioVoice?: string;
  cadenceNote?: string;
}

/**
 * Backend TTS Synthesis Request Payload
 */
export interface TTSVoiceRequest {
  text: string;
  mood?: AvatarPose | string;
  voice?: string;
  speed?: number;
  language?: string;
}

/**
 * Backend TTS Synthesis Response
 */
export interface TTSVoiceResponse {
  audioBlob: Blob | null;
  audioUrl?: string | null;
  subtitleCue: JapaneseSubtitleCue;
  japaneseSpeechText?: string;
  duration?: number;
}

/**
 * Real-time Voice Audio Synchronization State
 */
export interface VoicePlaybackSync {
  isPlaying: boolean;
  isLoading: boolean;
  progress: number; // 0.0 to 1.0
  currentTime: number;
  duration: number;
  subtitleCue: JapaneseSubtitleCue;
}

/**
 * Comprehensive Agnes Tachyon Japanese Catchphrases & Subtitle Cues catalog
 * Mapped to character expressive poses and moods.
 */
export const TACHYON_CUES_BY_POSE: Record<AvatarPose, JapaneseSubtitleCue> = {
  flow: {
    japanese: '「ふふっ… 私の光彩が見えるかい？ ククク…」',
    romaji: 'Fufu... watashi no kousai ga mieru kai? Kukuku...',
    englishCallout: 'Hehehe... can you perceive my brilliance? Kukuku...',
    mood: 'flow',
    audioVoice: 'jf_nezumi',
    cadenceNote: 'Eccentric transcendental cadence (1.10x speed, rapid pitch fluctuation)',
  },
  happy: {
    japanese: '「アッハハハ！ 実験大成功だねぇ、モルモット君！」',
    romaji: 'Ahhahaha! Jikken daiseikou da nee, Morumotto-kun!',
    englishCallout: 'Ahhahaha! A grand experimental success, my guinea pig!',
    mood: 'happy',
    audioVoice: 'jf_nezumi',
    cadenceNote: 'Exuberant manic laughter (+1.5 semitones, 1.08x speed)',
  },
  thinking: {
    japanese: '「興味深いねぇ… 実に興味深い仮説だよ。」',
    romaji: 'Kyoumibukai nee... jitsuni kyoumibukai kasetsu da yo.',
    englishCallout: 'Fascinating... a truly compelling hypothesis.',
    mood: 'thinking',
    audioVoice: 'jf_nezumi',
    cadenceNote: 'Slow analytical cadence (0.95x speed, contemplative drawl)',
  },
  serious: {
    japanese: '「実験開始だ。真理を暴き出そうじゃないか。」',
    romaji: 'Jikken kaishi da. Shinri wo abakidasou ja nai ka.',
    englishCallout: 'The experiment commences. Shall we unveil the underlying truth?',
    mood: 'serious',
    audioVoice: 'jf_nezumi',
    cadenceNote: 'Focused authoritative tone (-0.8 semitones, precise articulation)',
  },
  shocked: {
    japanese: '「な、なんだって？！ 計算外の異常事象だよ！」',
    romaji: 'Na, nandatte?! Keisangai no ijou jishou da yo!',
    englishCallout: 'Wh-what?! An anomalous incident outside my calculations!',
    mood: 'shocked',
    audioVoice: 'jf_nezumi',
    cadenceNote: 'Sharp gasp, frantic elevated pitch (+2.0 semitones, 1.15x speed)',
  },
  tired: {
    japanese: '「おや… エネルギー切れかい？ 休息もまた実験の過程さ。」',
    romaji: 'Oya... enerugii-gire kai? Kyuusoku mo mata jikken no katei sa.',
    englishCallout: 'My, my... running low on energy? Rest is also part of the protocol.',
    mood: 'tired',
    audioVoice: 'jf_nezumi',
    cadenceNote: 'Exhausted languid cadence (0.88x speed, relaxed breathy tone)',
  },
  idle: {
    japanese: '「ククク… ごきげんよう、我がモルモット君！」',
    romaji: 'Kukuku... gokigenyou, waga Morumotto-kun!',
    englishCallout: 'Kukuku... greetings, my dear guinea pig!',
    mood: 'idle',
    audioVoice: 'jf_nezumi',
    cadenceNote: 'Signature playful mad scientist smirk (1.04x speed)',
  },
};

/**
 * Contextual pattern matcher for situational dialogue cues
 */
interface ContextualCueRule {
  keywords: string[];
  cue: JapaneseSubtitleCue;
}

export const CONTEXTUAL_CUE_RULES: ContextualCueRule[] = [
  {
    keywords: ['rest', 'recovery', 'laziness', 'energy recovered', 'sleep', 'break'],
    cue: {
      japanese: '「休息もまた実験の重要な過程さ。ゆっくり休むといい、モルモット君。」',
      romaji: 'Kyuusoku mo mata jikken no juuyou na katei sa. Yukkuri yasumu to ii, Morumotto-kun.',
      englishCallout: 'Rest is an essential phase of our experiment. Take your time, guinea pig.',
      mood: 'tired',
      audioVoice: 'jf_nezumi',
      cadenceNote: 'Gentle patronizing cadence (0.92x speed)',
    },
  },
  {
    keywords: ['failure', 'catastrophe', 'incident', 'syntax error', 'panic', 'broken build', 'exception'],
    cue: {
      japanese: '「失敗も実験の醍醐味さ。だが、次は修正して見せたまえ！」',
      romaji: 'Shippai mo jikken no daigomi sa. Daga, tsugi wa shuusei shite misetamae!',
      englishCallout: 'Failure is the true thrill of experimentation. Now show me your remedy!',
      mood: 'shocked',
      audioVoice: 'jf_nezumi',
      cadenceNote: 'Sharp diagnostic excitement (1.12x speed)',
    },
  },
  {
    keywords: ['victory', 'champion', 'first place', 'cure', 'speed multiplier', 'grand derby'],
    cue: {
      japanese: '「見事だ、モルモット君！ 我々のアーキテクチャが圧倒的な勝利を掴んだよ！」',
      romaji: 'Migoto da, Morumotto-kun! Wareware no aakitekucha ga attouteki na shouri wo tsukanda yo!',
      englishCallout: 'Splendid, my guinea pig! Our architecture seized absolute victory!',
      mood: 'happy',
      audioVoice: 'jf_nezumi',
      cadenceNote: 'Triumphant manic crescendo (+1.8 semitones, 1.10x speed)',
    },
  },
  {
    keywords: ['greetings', 'chief architect', 'experiment', 'software experiment', 'welcome'],
    cue: {
      japanese: '「ククク… ごきげんよう、我がモルモット君！ ソフトウェア実験を始めよう！」',
      romaji: 'Kukuku... gokigenyou, waga Morumotto-kun! Sofutowea jikken wo hajimeyou!',
      englishCallout: 'Kukuku... greetings, my dear guinea pig! Shall we begin the software experiment?',
      mood: 'idle',
      audioVoice: 'jf_nezumi',
      cadenceNote: 'Enthusiastic mad scientist overture (1.04x speed)',
    },
  },
];

/**
 * Resolve the optimal Tachyon subtitle cue based on pose and contextual dialogue content.
 */
export function resolveTachyonSubtitleCue(pose: AvatarPose, dialogue?: string): JapaneseSubtitleCue {
  if (dialogue) {
    const lower = dialogue.toLowerCase();
    for (const rule of CONTEXTUAL_CUE_RULES) {
      if (rule.keywords.some((kw) => lower.includes(kw))) {
        return { ...rule.cue, mood: pose };
      }
    }
  }

  return TACHYON_CUES_BY_POSE[pose] || TACHYON_CUES_BY_POSE.idle;
}
