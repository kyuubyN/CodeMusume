export type AttributeType = 'speed' | 'stamina' | 'power' | 'guts' | 'wisdom';

export type StatRank = 'G' | 'F' | 'E' | 'D' | 'C' | 'B' | 'A' | 'S' | 'SS';

export type MoodState = 'terrible' | 'poor' | 'normal' | 'good' | 'great';

export type AvatarPose = 'idle' | 'thinking' | 'shocked' | 'happy' | 'serious' | 'tired' | 'flow';

export interface AttributeScores {
  speed: number;
  stamina: number;
  power: number;
  guts: number;
  wisdom: number;
}

export interface GameState {
  repo_name: string;
  turn: number;
  max_turns: number;
  energy: number;
  mood: MoodState;
  attributes: AttributeScores;
  current_pose: AvatarPose;
  dialogue: string;
  is_game_over: boolean;
  interactions_in_cycle?: number;
  interactions_required?: number;
  race_unlocked?: boolean;
  learned_insights?: string[];
}

export interface TrainResult {
  success: boolean;
  attribute: AttributeType;
  stat_gained: number;
  energy_spent: number;
  failure_rate: number;
  tachyon_commentary: string;
  pose: AvatarPose;
  updated_state: GameState;
  mcp_insight?: string | null;
}

export interface RestResult {
  energy_recovered: number;
  new_mood: MoodState;
  tachyon_commentary: string;
  updated_state: GameState;
}

export interface RaceRival {
  id: string;
  name: string;
  architecture_style: string;
  attributes: AttributeScores;
  current_distance: number;
  status: string;
}

export interface RaceIncident {
  sector: number;
  distance_m: number;
  name: string;
  tested_attribute: AttributeType;
  description: string;
  player_success: boolean;
  tachyon_callout: string;
}

export interface RaceTick {
  tick: number;
  distance_m: number;
  player_distance: number;
  rivals: RaceRival[];
  active_incident: RaceIncident | null;
  commentary: string | null;
  is_finished: boolean;
}

export interface CurriculumCard {
  title: string;
  primary_pattern: string;
  authorities: string[];
  core_principle: string;
  cutscene: {
    title: string;
    image_cue: string;
    description: string;
  };
  canonical_remedy: string;
}

export interface QuizQuestion {
  id: string;
  question: string;
  options: string[];
  tested_attribute: AttributeType;
  context_hint?: string | null;
}

export interface QuizEvaluationResponse {
  correct: boolean;
  correct_index: number;
  explanation: string;
  speed_delta: number;
}

