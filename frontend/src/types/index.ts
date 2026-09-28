export type AttributeType = 'speed' | 'stamina' | 'power' | 'guts' | 'wisdom';

export type StatRank = 'G' | 'F' | 'E' | 'D' | 'C' | 'B' | 'A' | 'S' | 'SS';

export type MoodState = 'terrible' | 'poor' | 'normal' | 'good' | 'great';

export type AvatarPose = 'idle' | 'thinking' | 'shocked' | 'happy' | 'serious' | 'tired' | 'flow' | 'crazy';

export interface AttributeScores {
  speed: number;
  stamina: number;
  power: number;
  guts: number;
  wisdom: number;
}

export interface GameState {
  mode?: 'lab' | 'repo';
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


export interface CodeSmell {
  id: number;
  key: string;
  attribute: AttributeType;
  rule_id: string;
  file_path: string;
  line_number: number;
  description: string;
  tachyon_critique: string;
  suggested_fix: string;
  code_snippet: string;
  drilled: boolean;
}

/** Screen hints returned with every tool call. */
export interface ToolUi {
  panel?: 'smells' | 'smell' | 'prescription' | 'experiment' | 'review' | 'lab' | 'standards';
  attribute?: AttributeType | null;
  smell_id?: number | null;
  prescription?: string;
  view?: 'race';
  event?:
    | 'train'
    | 'rest'
    | 'rescan'
    | 'experiment_start'
    | 'prediction'
    | 'evidence'
    | 'explanation'
    | 'hint'
    | 'fix'
    | 'revert'
    | 'debrief'
    | 'abandon'
    | 'review_start'
    | 'review_answer';
  script?: string[];
  correct?: boolean;
  accepted?: boolean;
  verdict?: FixVerdict;
  score?: number;
  eureka?: boolean;
  success?: boolean;
  gained?: number;
  energy_recovered?: number;
  fixed?: number[];
  new?: number[];
  deltas?: Record<AttributeType, number>;
}

export interface ToolOutcome {
  result: Record<string, unknown>;
  state: GameState;
  ui: ToolUi;
  lab?: LabState | null;
}

// ---------------------------------------------------------------------------
// Lab career
// ---------------------------------------------------------------------------

export type FixVerdict = 'best' | 'good' | 'partial' | 'wrong';
export type Stage = 'predict' | 'evidence' | 'explain' | 'fix' | 'reprove' | 'debrief';

export interface Headline {
  label: string;
  value: number;
  unit: string;
}

export interface Measurement {
  metrics?: Record<string, number | boolean | string>;
  headline?: Headline;
  series?: { x: string; y: string; points: [number, number][]; flags?: Record<string, string> };
  notes?: string[];
  calls?: { function: string; calls: number }[];
  audit?: Record<string, number>;
  graph?: {
    nodes: { id: string; loaded: boolean; blast_radius: number; instability: number }[];
    edges: { src: string; dst: string; lazy: boolean; cycle: boolean }[];
  };
  loaded?: string[];
  error?: string;
  wall_ms?: number;
  python?: string;
}

export interface FixView {
  key: string;
  label: string;
  detail: string;
  verdict: FixVerdict | null;
  lesson: string | null;
  diff: string;
}

export interface FixTryView {
  key: string;
  verdict: FixVerdict;
  score: number;
  static: string;
  result: Measurement;
}

export interface DebriefSummary {
  chapter: number;
  title: string;
  score: number;
  points: Record<string, number>;
  multiplier: number;
  eureka: boolean;
  mastery_before: number;
  mastery_after: number;
  next_review_in_days: number;
  stat: AttributeType;
  stat_before: number;
  stat_after: number;
  rank_after: StatRank;
  fix: string;
  fix_verdict: FixVerdict;
  first_fix_verdict: FixVerdict;
  bond_gained: number;
  bond: number;
  bond_title: string;
  title_up: boolean;
  lore: { title: string; text: string } | null;
  takeaway: string;
  derby_unlocked: boolean;
}

export interface ExperimentView {
  chapter: number;
  title: string;
  concept: string;
  stat: AttributeType;
  stage: Stage;
  eureka: boolean;
  intro: string[];
  question: string;
  options: string[];
  prediction: { index: number; confidence: number; correct: boolean } | null;
  correct_index: number | null;
  baseline: Measurement | null;
  baseline_score: number;
  code_file: string;
  code: string[];
  evidence_prompt: string;
  evidence_attempts: number[];
  evidence_found: 'best' | 'ok' | 'revealed' | null;
  evidence_lines: number[];
  evidence_ok_lines: number[];
  explain_prompt: string;
  explanations: string[];
  rubric: { id: string; label: string; hit: boolean }[];
  rubric_revealed: boolean;
  follow_up: string | null;
  hints: string[];
  hints_left: number;
  fix_prompt: string;
  fixes: FixView[];
  tries: FixTryView[];
  current_fix: string | null;
  after: Measurement | null;
  after_score: number | null;
  points: Record<string, number>;
  summary: DebriefSummary | null;
}

export interface ChapterView {
  id: number;
  slug: string;
  title: string;
  concept: string;
  stat: AttributeType;
  status: 'open' | 'active' | 'cleared';
  score: number | null;
  fix: string | null;
  measure: Headline | null;
  error: string | null;
}

export interface MasteryView {
  concept: string;
  title: string;
  stat: AttributeType;
  chapter: number;
  mastery: number;
  box: number;
  due: boolean;
  due_in: number | null;
  sparks: number;
  reviews: [number, number];
}

export interface HallEntry {
  career: number;
  finished_at: string;
  trainee: string;
  place: number;
  checkpoint_score: number;
  attributes: Record<AttributeType, number>;
  chapters_cleared: number[];
  sparks: Record<string, number>;
}

export interface ReviewView {
  id: string;
  concept: string;
  prompt: string;
  code: string;
  options: string[];
  answered: number | null;
  correct_index: number | null;
  explanation: string | null;
}

export interface LabState {
  mode: 'lab' | 'repo';
  career: number;
  lab_day: number;
  bond: number;
  title: string;
  calibration: number | null;
  predictions: [number, number];
  certain: [number, number];
  chapters: ChapterView[];
  mastery: MasteryView[];
  due: string[];
  sparks: Record<string, number>;
  skills: { concept: string; title: string; stat: AttributeType; level: number }[];
  hall: HallEntry[];
  journal: { chapter: number; title: string; text: string }[];
  experiment: ExperimentView | null;
  review: ReviewView | null;
  experiments_done: number;
  experiments_required: number;
}

export interface LabSnapshot {
  state: GameState;
  lab: LabState;
}

export interface DerbyQuestion {
  id: string;
  concept: string;
  question: string;
  code: string;
  options: string[];
}

export interface DerbySetup {
  ticks: RaceTick[];
  runners: { id: string; name: string }[];
  questions: DerbyQuestion[];
  skills: { concept: string; title: string; stat: AttributeType; level: number }[];
  attributes: AttributeScores;
}

export interface CareerSummary {
  hall_entry: HallEntry;
  sparks_earned: Record<string, number>;
  bond: number;
  title: string;
  next_career: number;
  state: GameState;
  lab: LabState;
}


// ---------------------------------------------------------------------------
// Architecture standards (free lab)
// ---------------------------------------------------------------------------

export interface StandardsCheck {
  id: string;
  title: string;
  stat: AttributeType;
  chapter: number;
  status: 'pass' | 'warn' | 'fail';
  value: string;
  target: string;
  detail: string;
  evidence: { file: string; line: number; code: string; note: string }[];
}

export interface StandardsReport {
  root: string;
  files: number;
  modules: number;
  lines: number;
  parse_errors: string[];
  passed: number;
  total: number;
  grade: string;
  checks: StandardsCheck[];
  graph: NonNullable<Measurement['graph']> & { truncated: boolean };
  scores: AttributeScores;
}
