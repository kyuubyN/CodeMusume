import type { AttributeType, AvatarPose, StatRank } from '../types';

export interface StatMeta {
  key: AttributeType;
  label: string;
  short: string;
  blurb: string;
  color: string;
  image: string;
}

export const STATS: StatMeta[] = [
  { key: 'speed', label: 'Speed', short: 'SPD', blurb: 'Latency & blocking I/O', color: '#2a9fbf', image: '/assets/animations/speed_training.png' },
  { key: 'stamina', label: 'Stamina', short: 'STA', blurb: 'Resource lifetimes', color: '#c2417a', image: '/assets/animations/stamina_training.png' },
  { key: 'power', label: 'Power', short: 'POW', blurb: 'Throughput & batching', color: '#c98a00', image: '/assets/animations/power_training.jpeg' },
  { key: 'guts', label: 'Guts', short: 'GUT', blurb: 'Errors & timeouts', color: '#e5484d', image: '/assets/animations/guts_training.jpeg' },
  { key: 'wisdom', label: 'Wisdom', short: 'WIS', blurb: 'Types & structure', color: '#1f9d55', image: '/assets/animations/wise_training.jpeg' },
];

export const STAT_BY_KEY = Object.fromEntries(STATS.map((s) => [s.key, s])) as Record<AttributeType, StatMeta>;

export function rankOf(score: number): StatRank {
  if (score >= 1150) return 'SS';
  if (score >= 1000) return 'S';
  if (score >= 800) return 'A';
  if (score >= 700) return 'B';
  if (score >= 600) return 'C';
  if (score >= 500) return 'D';
  if (score >= 400) return 'E';
  if (score >= 200) return 'F';
  return 'G';
}

/** Top ranks get the accent; everything else stays monochrome. */
export function rankIsHigh(rank: StatRank): boolean {
  return rank === 'SS' || rank === 'S' || rank === 'A';
}

/** Stat bars fill toward the S rank. */
export const STAT_BAR_MAX = 1000;

/** Mood as a 5-step level (Endfield-style segmented meter). */
export const MOOD_LEVEL: Record<string, { label: string; level: number }> = {
  great: { label: 'Great', level: 5 },
  good: { label: 'Good', level: 4 },
  normal: { label: 'Normal', level: 3 },
  poor: { label: 'Poor', level: 2 },
  terrible: { label: 'Awful', level: 1 },
};

/** Pick an expressive sprite for a line Agnes just said. */
export function poseForLine(text: string, energy: number, mood: string): AvatarPose {
  const t = text.toLowerCase();
  if (energy < 25) return 'tired';
  if (/(disaster|catastroph|how dare|unacceptable|necrosis|leak|swallow|outrage|what\?!|failed)/.test(t)) return 'shocked';
  if (/(hmm|let me|let us|ponder|curious|perhaps|which|consider|examine|wonder)/.test(t)) return 'thinking';
  if (/(must|never|strict|warn|listen|serious|discipline|crucial)/.test(t)) return 'serious';
  if (/(splendid|magnificent|excellent|wonderful|brilliant|delight|victory|fixed|well done|eureka)/.test(t)) {
    return mood === 'great' ? 'flow' : 'happy';
  }
  if (/(kukuku|hehehe|ufufu)/.test(t)) return 'happy';
  return 'idle';
}
