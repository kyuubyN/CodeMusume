import {
  AttributeType,
  CurriculumCard,
  GameState,
  QuizEvaluationResponse,
  QuizQuestion,
  RaceTick,
  RestResult,
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
};
