import {
  AttributeType,
  CareerSummary,
  CodeSmell,
  DerbySetup,
  LabSnapshot,
  StandardsReport,
  CurriculumCard,
  GameState,
  QuizEvaluationResponse,
  QuizQuestion,
  RaceTick,
  RestResult,
  ToolOutcome,
  TrainResult,
} from '../types';

const API_BASE = '/api';

export const api = {
  async getState(): Promise<GameState> {
    const res = await fetch(`${API_BASE}/state`);
    if (!res.ok) throw new Error('Failed to fetch game state');
    return res.json();
  },

  async scanRepo(targetPath = '.'): Promise<GameState> {
    const res = await fetch(`${API_BASE}/scan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_path: targetPath }),
    });
    if (!res.ok) throw new Error('Failed to scan repository');
    return res.json();
  },

  async train(attribute: AttributeType, customKnowledge?: string): Promise<TrainResult> {
    const res = await fetch(`${API_BASE}/train`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ attribute, custom_knowledge: customKnowledge }),
    });
    if (!res.ok) throw new Error('Training request failed');
    return res.json();
  },

  async rest(): Promise<RestResult> {
    const res = await fetch(`${API_BASE}/rest`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Rest request failed');
    return res.json();
  },

  async simulateRace(): Promise<RaceTick[]> {
    const res = await fetch(`${API_BASE}/race/simulate`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Race simulation failed');
    return res.json();
  },

  async sendDialogue(event: string): Promise<{ dialogue: string; pose: string }> {
    const res = await fetch(`${API_BASE}/dialogue`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event }),
    });
    if (!res.ok) throw new Error('Dialogue request failed');
    return res.json();
  },

  async getCurriculum(attribute: AttributeType): Promise<CurriculumCard> {
    const res = await fetch(`${API_BASE}/training/curriculum/${attribute}`);
    if (!res.ok) throw new Error('Failed to fetch curriculum');
    return res.json();
  },

  async synthesizeAudio(text: string): Promise<Blob | null> {
    try {
      const res = await fetch(`${API_BASE}/audio/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice: 'af_bella' }),
      });
      if (res.status === 204 || !res.ok) return null;
      return await res.blob();
    } catch {
      return null;
    }
  },

  async getRaceQuiz(): Promise<QuizQuestion[]> {
    const res = await fetch(`${API_BASE}/race/quiz`);
    if (!res.ok) throw new Error('Failed to fetch race quiz');
    return res.json();
  },

  async evaluateRaceQuiz(questionId: string, selectedIndex: number): Promise<QuizEvaluationResponse> {
    const res = await fetch(`${API_BASE}/race/evaluate-quiz`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_id: questionId, selected_index: selectedIndex }),
    });
    if (!res.ok) throw new Error('Quiz evaluation failed');
    return res.json();
  },

  async completeRace(place = 1, pointsAwarded = 0): Promise<GameState> {
    const res = await fetch(`${API_BASE}/race/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ place, points_awarded: pointsAwarded }),
    });
    if (!res.ok) throw new Error('Failed to complete race');
    return res.json();
  },

  async getSmells(): Promise<CodeSmell[]> {
    const res = await fetch(`${API_BASE}/smells`);
    if (!res.ok) throw new Error('Failed to fetch smells');
    return res.json();
  },

  async getPrescription(smellId: number): Promise<string> {
    const res = await fetch(`${API_BASE}/smells/${smellId}/prescription`);
    if (!res.ok) throw new Error('Failed to fetch prescription');
    return (await res.json()).prescription;
  },

  async resetGame(): Promise<GameState> {
    const res = await fetch(`${API_BASE}/reset`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to reset');
    return res.json();
  },

  /** Execute a game action through the same dispatcher the voice agent uses. */
  async runTool(name: string, args: Record<string, unknown> = {}): Promise<ToolOutcome> {
    const res = await fetch(`${API_BASE}/voice/tool`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, arguments: args }),
    });
    if (!res.ok) throw new Error(`Tool ${name} failed`);
    return res.json();
  },

  async getRepoReport(): Promise<StandardsReport> {
    const res = await fetch(`${API_BASE}/repo/report`);
    if (!res.ok) throw new Error('Failed to build the architecture report');
    return res.json();
  },

  // ---- Lab career --------------------------------------------------------

  async getLab(): Promise<LabSnapshot> {
    const res = await fetch(`${API_BASE}/lab`);
    if (!res.ok) throw new Error('Failed to load the lab');
    return res.json();
  },

  /** Enter the lab: resume the current career, or start a fresh one. */
  async startCareer(fresh = false): Promise<LabSnapshot> {
    const res = await fetch(`${API_BASE}/lab/career`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ fresh }),
    });
    if (!res.ok) throw new Error('Failed to start a career');
    return res.json();
  },

  async closeLabPanel(): Promise<LabSnapshot> {
    const res = await fetch(`${API_BASE}/lab/close`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to close');
    return res.json();
  },

  async setupDerby(): Promise<DerbySetup> {
    const res = await fetch(`${API_BASE}/lab/derby`, { method: 'POST' });
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || 'The Derby could not start');
    }
    return res.json();
  },

  async answerCheckpoint(questionId: string, selectedIndex: number): Promise<QuizEvaluationResponse> {
    const res = await fetch(`${API_BASE}/lab/derby/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_id: questionId, selected_index: selectedIndex }),
    });
    if (!res.ok) throw new Error('Checkpoint evaluation failed');
    return res.json();
  },

  async completeDerby(place: number, checkpointScore: number): Promise<CareerSummary> {
    const res = await fetch(`${API_BASE}/lab/derby/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ place, checkpoint_score: checkpointScore }),
    });
    if (!res.ok) throw new Error('Failed to finish the career');
    return res.json();
  },

  async getVoiceToken(): Promise<string> {
    const res = await fetch(`${API_BASE}/voice/token`);
    if (!res.ok) {
      const detail = await res.json().catch(() => ({}));
      throw new Error(detail.detail || 'Could not get a voice token');
    }
    return (await res.json()).token;
  },

  async getVoiceSession(): Promise<Record<string, unknown>> {
    const res = await fetch(`${API_BASE}/voice/session`);
    if (!res.ok) throw new Error('Failed to load voice session config');
    return res.json();
  },

  async getVoicePrompt(): Promise<string> {
    const res = await fetch(`${API_BASE}/voice/prompt`);
    if (!res.ok) throw new Error('Failed to load voice prompt');
    return (await res.json()).system_prompt;
  },
};
