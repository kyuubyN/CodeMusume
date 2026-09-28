import React, { useCallback, useEffect, useRef, useState } from 'react';
import confetti from 'canvas-confetti';
import type {
  AttributeType,
  AvatarPose,
  CareerSummary,
  CodeSmell,
  DerbyQuestion,
  GameState,
  LabState,
  ToolOutcome,
} from './types';
import { api } from './services/api';
import { audioService, sounds } from './services/audio';
import type { ToolCall } from './services/voiceAgent';
import { useVoiceAgent } from './hooks/useVoiceAgent';
import { STATS, STAT_BY_KEY, poseForLine } from './lib/game';
import { TopBar } from './components/TopBar';
import { StatsPanel } from './components/StatsPanel';
import { CaseFile, CaseView } from './components/CaseFile';
import { AgnesAvatar } from './components/AgnesAvatar';
import { VoiceDock } from './components/VoiceDock';
import { EventLayer, CutIn, Toast } from './components/EventLayer';
import { RaceView, QuizAnswerResult } from './components/RaceView';
import { CareerResult } from './components/CareerResult';
import { ExperimentBench } from './components/lab/ExperimentBench';
import { LabBoard } from './components/lab/LabBoard';
import { Dossier } from './components/lab/Dossier';
import { ReviewCard } from './components/lab/ReviewCard';
import { StandardsReport } from './components/lab/StandardsReport';
import { LAB_TOUR, Tutorial, TourStep, guideSeen, markGuideSeen } from './components/Tutorial';

const EMPTY_STATE: GameState = {
  mode: 'lab',
  repo_name: '…',
  turn: 1,
  max_turns: 12,
  energy: 100,
  mood: 'normal',
  attributes: { speed: 0, stamina: 0, power: 0, guts: 0, wisdom: 0 },
  current_pose: 'idle',
  dialogue: '',
  is_game_over: false,
  interactions_in_cycle: 0,
  interactions_required: 3,
  race_unlocked: false,
};

const POKE_LINES = [
  'Kukuku… conducting tactile experiments on your scientist, Morumotto-kun?',
  'Hands off the apparatus! Poke the code instead. It needs it more.',
  'Hehehe… curiosity is the first symptom of a good researcher.',
];

type Tab = 'lab' | 'dossier' | 'case' | 'standards';
let uid = 1;
const pad = (n: number) => String(n).padStart(2, '0');

export const App: React.FC = () => {
  const [game, setGame] = useState<GameState>(EMPTY_STATE);
  const [lab, setLab] = useState<LabState | null>(null);
  const [smells, setSmells] = useState<CodeSmell[]>([]);
  const [view, setView] = useState<'training' | 'race'>('training');
  const [tab, setTab] = useState<Tab>('lab');
  const [caseView, setCaseView] = useState<CaseView>({ mode: 'list' });
  const [highlight, setHighlight] = useState<number[]>([]);
  const [pose, setPose] = useState<AvatarPose>('idle');
  const [busy, setBusy] = useState(false);
  const [textBusy, setTextBusy] = useState(false);
  const [cutIn, setCutIn] = useState<CutIn | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [flash, setFlash] = useState<Partial<Record<AttributeType, number>>>({});
  const [drawer, setDrawer] = useState<'stats' | 'side' | null>(null);
  const [backendDown, setBackendDown] = useState(false);
  const [career, setCareer] = useState<CareerSummary | null>(null);
  const [tour, setTour] = useState(false);
  const [reportVersion, setReportVersion] = useState(0);
  const quizAnswerRef = useRef<((i: number) => Promise<QuizAnswerResult>) | null>(null);
  const pokeCount = useRef(0);
  const gameRef = useRef(game);
  gameRef.current = game;

  const inLab = game.mode === 'lab';

  const toast = useCallback((tone: Toast['tone'], title: string, body?: string) => {
    setToasts((t) => [...t.slice(-2), { id: uid++, tone, title, body }]);
  }, []);

  /** New game state, with a flash on every stat that moved. */
  const takeState = useCallback((s: GameState) => {
    const prev = gameRef.current;
    const delta: Partial<Record<AttributeType, number>> = {};
    if (prev.repo_name !== '…' && prev.mode === s.mode) {
      for (const st of STATS) {
        const d = s.attributes[st.key] - prev.attributes[st.key];
        if (d) delta[st.key] = d;
      }
    }
    if (Object.keys(delta).length) setFlash(delta);
    setGame(s);
  }, []);

  const refreshSmells = useCallback(async () => {
    try {
      setSmells(await api.getSmells());
    } catch {
      /* keep the last list */
    }
  }, []);

  const loadAll = useCallback(async () => {
    try {
      const [snap, list] = await Promise.all([api.getLab(), api.getSmells()]);
      setGame(snap.state);
      setLab(snap.lab);
      setSmells(list);
      setPose(snap.state.current_pose);
      setTab(snap.state.mode === 'lab' ? 'lab' : 'standards');
      setBackendDown(false);
      return snap;
    } catch {
      setBackendDown(true);
      return null;
    }
  }, []);

  // ---- Voice agent -------------------------------------------------------

  const applyRef = useRef<(out: ToolOutcome, source: 'voice' | 'ui') => void>(() => {});

  const handleToolCall = useCallback(async (call: ToolCall): Promise<unknown> => {
    if (call.name === 'answer_quiz') {
      const fn = quizAnswerRef.current;
      if (!fn) return { error: 'No checkpoint question is open right now.' };
      const letter = String(call.args.option ?? '').trim().toUpperCase();
      const i = 'ABCD'.indexOf(letter);
      if (i < 0) return { error: 'Option must be A, B, C or D.' };
      return fn(i);
    }
    const out = await api.runTool(call.name, call.args);
    applyRef.current(out, 'voice');
    return out.result;
  }, []);

  const voice = useVoiceAgent(handleToolCall);

  useEffect(() => {
    void loadAll().then((snap) => {
      if (!snap) return;
      const l = snap.lab;
      const greeting =
        snap.state.mode !== 'lab'
          ? `Kukuku… I dissected ${snap.state.repo_name}. Open a case on the right, or open the voice link and ask me what is wrong.`
          : l.experiment && l.experiment.stage !== 'debrief'
            ? `Back to the bench, Morumotto-kun. Experiment ${pad(l.experiment.chapter)} is waiting.`
            : l.due.length
              ? 'Welcome back, Morumotto-kun. A pop quiz is due before anything else.'
              : l.predictions[1] === 0
                ? 'Kukuku… a new test subject. This lab trains code, and I measure everything. Start experiment 01, or open the voice link and talk to me.'
                : `Welcome back, Morumotto-kun. Career ${pad(l.career)}, day ${l.lab_day}. Shall we continue?`;
      voice.push('agnes', greeting);
      if (!guideSeen() && window.innerWidth >= 1024) setTour(true);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Browsers block autoplay; start the soundtrack on the first interaction.
  useEffect(() => {
    const start = () => audioService.playBGM();
    window.addEventListener('pointerdown', start, { once: true });
    return () => window.removeEventListener('pointerdown', start);
  }, []);

  const openSide = useCallback((t: Tab) => {
    setTab(t);
    if (window.innerWidth < 1280) setDrawer('side');
  }, []);

  /** Reflect a tool outcome on screen (shared by voice and on-screen buttons). */
  const applyOutcome = useCallback(
    (out: ToolOutcome, source: 'voice' | 'ui') => {
      const { ui, result, state } = out;
      takeState(state);
      if (out.lab) setLab(out.lab);
      setPose(state.current_pose);
      if (state.mode !== 'lab') void refreshSmells();

      if (ui.panel === 'smells') {
        setCaseView({ mode: 'list', attribute: ui.attribute ?? null });
        openSide('case');
      }
      if (ui.panel === 'smell' && ui.smell_id) {
        setCaseView({ mode: 'detail', smellId: ui.smell_id });
        setHighlight([ui.smell_id]);
        openSide('case');
      }
      if (ui.panel === 'prescription' && ui.smell_id && ui.prescription) {
        setCaseView({ mode: 'prescription', smellId: ui.smell_id, text: ui.prescription });
        openSide('case');
      }
      if (ui.panel === 'experiment' || ui.panel === 'review') openSide('lab');
      if (ui.panel === 'standards') openSide('standards');

      const exp = out.lab?.experiment;
      switch (ui.event) {
        case 'experiment_start':
          sounds.playSkill();
          setCutIn(
            ui.eureka
              ? { id: uid++, kicker: 'Bond resonance', title: 'Eureka', detail: 'rewards ×1.5 this experiment', tone: 'acc' }
              : { id: uid++, kicker: `Experiment ${pad(exp?.chapter ?? 0)}`, title: exp?.title ?? 'Begin', detail: exp?.concept, tone: 'acc' }
          );
          break;
        case 'prediction':
          if (ui.correct) {
            sounds.playSuccess();
            setCutIn({ id: uid++, kicker: 'Hypothesis', title: 'Confirmed', detail: String(result.measured ?? ''), tone: 'good' });
          } else {
            sounds.playFailure();
            setCutIn(
              result.certain_and_wrong
                ? { id: uid++, kicker: 'Certain, and', title: 'Wrong', detail: 'this is the one you will remember', tone: 'bad' }
                : { id: uid++, kicker: 'Hypothesis', title: 'Refuted', detail: String(result.measured ?? ''), tone: 'bad' }
            );
          }
          break;
        case 'evidence':
          if (ui.accepted) {
            sounds.playSkill();
            setCutIn({ id: uid++, kicker: 'Objection', title: 'Sustained', detail: `line ${String(result.line ?? result.revealed_line ?? '')}`, tone: 'acc' });
          } else sounds.playFailure();
          break;
        case 'fix': {
          const good = ui.verdict === 'best' || ui.verdict === 'good';
          if (good) sounds.playSuccess();
          else sounds.playFailure();
          setCutIn({
            id: uid++,
            kicker: 'Treatment',
            title: ui.verdict === 'best' ? 'Cured' : ui.verdict === 'good' ? 'Improved' : ui.verdict === 'partial' ? 'Partial' : 'No cure',
            detail: `${String(result.before ?? '')} → ${String(result.after ?? '')}`,
            tone: good ? 'good' : 'bad',
          });
          break;
        }
        case 'debrief':
          sounds.playSuccess();
          setCutIn({ id: uid++, kicker: 'Experiment complete', title: `${ui.score ?? 0} / 100`, detail: ui.eureka ? 'eureka ×1.5' : undefined, tone: 'acc' });
          if ((ui.score ?? 0) >= 80) {
            window.setTimeout(() => confetti({ particleCount: 90, spread: 70, origin: { y: 0.6 }, colors: ['#ffe100', '#141517', '#f1f1ee'] }), 400);
          }
          break;
        case 'review_answer':
          if (ui.correct) sounds.playSuccess();
          else sounds.playFailure();
          toast(ui.correct ? 'good' : 'bad', ui.correct ? 'Recalled' : 'Not yet', ui.correct ? 'Next review comes later.' : 'Back to box 1.');
          break;
        case 'train':
          if (ui.attribute) {
            const stat = STAT_BY_KEY[ui.attribute];
            setCutIn({
              id: uid++,
              kicker: ui.success ? 'Training' : 'Training failed',
              title: stat.label,
              detail: ui.success ? `+${ui.gained ?? 0}${ui.smell_id ? ` · drilled case ${pad(ui.smell_id)}` : ''}` : 'mood down',
              tone: ui.success ? 'good' : 'bad',
              image: stat.image,
            });
            if (ui.success) sounds.playSuccess();
            else sounds.playFailure();
          }
          break;
        case 'rest':
          sounds.playSuccess();
          toast('info', `Rested · +${ui.energy_recovered ?? 0} energy`, `Mood: ${state.mood}`);
          break;
        case 'rescan': {
          setReportVersion((v) => v + 1);
          const fixed = ui.fixed?.length ?? 0;
          const added = ui.new?.length ?? 0;
          const gains = Object.entries(ui.deltas ?? {})
            .filter(([, v]) => v)
            .map(([k, v]) => `${STAT_BY_KEY[k as AttributeType].label} ${v > 0 ? '+' : ''}${v}`)
            .join(' · ');
          if (fixed) {
            sounds.playSuccess();
            toast('good', `${fixed} smell${fixed > 1 ? 's' : ''} fixed for real`, gains || undefined);
          } else if (added) {
            sounds.playFailure();
            toast('bad', `${added} new smell${added > 1 ? 's' : ''} appeared`, gains || undefined);
            setHighlight(ui.new ?? []);
          } else {
            toast('info', 'Rescan complete', 'No changes detected in the code.');
          }
          break;
        }
        default:
          break;
      }

      if (ui.view === 'race') {
        sounds.playRaceStart();
        setView('race');
      }
      // Without a live voice, Agnes's scripted lines appear in the dock.
      if (!voice.live && ui.script?.length) voice.push('agnes', ui.script.join(' '));
      if (typeof result.error === 'string') {
        if (source === 'ui' || !voice.live) toast('bad', String(result.error));
        if (!voice.live) voice.push('agnes', String(result.error));
      }
      if (voice.live) void voice.refreshPrompt();
    },
    [takeState, refreshSmells, openSide, toast, voice]
  );
  applyRef.current = applyOutcome;

  // Agnes's latest line drives her expression.
  const lastLine = voice.log[voice.log.length - 1];
  useEffect(() => {
    if (lastLine?.role === 'agnes' && voice.live) setPose(poseForLine(lastLine.text, game.energy, game.mood));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lastLine?.id]);

  useEffect(() => {
    if (voice.status === 'thinking') setPose((p) => (p === 'idle' ? 'thinking' : p));
  }, [voice.status]);

  // ---- On-screen actions ---------------------------------------------------

  const runAction = useCallback(
    async (name: string, args: Record<string, unknown>, label: string) => {
      if (busy) return;
      setBusy(true);
      sounds.playClick();
      try {
        const out = await api.runTool(name, args);
        applyOutcome(out, 'ui');
        if (voice.live) {
          const { say, ...rest } = out.result as Record<string, unknown>;
          voice.notify(
            `The trainer pressed "${label}" on screen; it already happened, do not call the tool again. Result: ${JSON.stringify(rest).slice(0, 1400)}` +
              (say ? ` Next: ${String(say)}` : ' React briefly, in character.')
          );
        } else {
          voice.push('event', label);
        }
      } catch {
        toast('bad', 'The lab backend is not responding.');
      } finally {
        setBusy(false);
      }
    },
    [busy, applyOutcome, voice, toast]
  );

  const handlePoke = () => {
    sounds.playClick();
    if (voice.live) {
      voice.notify('The trainer just poked you on screen. React playfully in one short sentence.');
      return;
    }
    const line = POKE_LINES[pokeCount.current++ % POKE_LINES.length];
    voice.push('agnes', line);
    setPose(pokeCount.current % 2 ? 'shocked' : 'happy');
  };

  const handleTextFallback = async (text: string) => {
    // Typing during the explain step is the explanation.
    if (lab?.experiment?.stage === 'explain') {
      voice.push('user', text);
      await runAction('submit_explanation', { explanation: text }, 'Explain');
      return;
    }
    voice.push('user', text);
    setTextBusy(true);
    try {
      const resp = await api.sendDialogue(text);
      voice.push('agnes', resp.dialogue);
      setPose((resp.pose as AvatarPose) || 'idle');
    } catch {
      toast('bad', 'Agnes could not answer. Is the backend running?');
    } finally {
      setTextBusy(false);
    }
  };

  const enterLab = async () => {
    setBusy(true);
    try {
      const snap = await api.startCareer(false);
      setGame(snap.state);
      setLab(snap.lab);
      setTab('lab');
      setPose('happy');
      toast('info', 'Back in the lab', `Career ${pad(snap.lab.career)} · day ${snap.lab.lab_day}`);
      if (voice.live) {
        void voice.refreshPrompt();
        voice.notify('The trainer switched back to your lab and the tachyon_lab specimen. Welcome them back in one sentence and suggest the next experiment.');
      }
    } catch {
      toast('bad', 'Could not open the lab.');
    } finally {
      setBusy(false);
    }
  };

  const handleScanRepo = async (path: string) => {
    setBusy(true);
    try {
      const s = await api.scanRepo(path);
      setGame(s);
      setPose('thinking');
      await refreshSmells();
      const snap = await api.getLab();
      setLab(snap.lab);
      setCaseView({ mode: 'list' });
      setTab('standards');
      setReportVersion((v) => v + 1);
      toast('info', `Scanned ${s.repo_name}`, 'Free lab: ten architecture checks on your code.');
      if (voice.live) {
        void voice.refreshPrompt();
        voice.notify(`The trainer switched to the free lab on their own repository: ${s.repo_name}. You have dissected it. Summarize the worst finding in one sentence.`);
      } else {
        voice.push('agnes', `Kukuku… ${s.repo_name}, dissected. The standards check is on the right. Shall we start with the worst failure?`);
      }
    } catch {
      toast('bad', 'Could not scan that path.');
    } finally {
      setBusy(false);
    }
  };

  /** From a failing standards check: go learn the concept in the lab. */
  const practiceChapter = async (chapter: number) => {
    setBusy(true);
    let snap;
    try {
      snap = await api.startCareer(false);
      setGame(snap.state);
      setLab(snap.lab);
      setTab('lab');
    } catch {
      toast('bad', 'Could not open the lab.');
      return;
    } finally {
      setBusy(false);
    }
    const ch = snap.lab.chapters.find((c) => c.id === chapter);
    const running = snap.lab.experiment && snap.lab.experiment.stage !== 'debrief';
    if (ch?.status === 'open' && !running && !snap.state.is_game_over) {
      await runAction('start_experiment', { chapter }, `Start experiment ${pad(chapter)} to learn a failing check`);
    } else {
      toast('info', `Chapter ${pad(chapter)} · ${ch?.title ?? ''}`, ch?.status === 'cleared' ? 'Already cleared this career. Your Dossier keeps the lesson.' : undefined);
    }
    if (voice.live) void voice.refreshPrompt();
  };

  const openCaseAt = (file: string, line: number) => {
    const hit = smells.find((sm) => sm.line_number === line && (sm.file_path === file || sm.file_path.endsWith(`/${file}`)));
    setCaseView(hit ? { mode: 'detail', smellId: hit.id } : { mode: 'list' });
    if (hit) setHighlight([hit.id]);
    setTab('case');
  };

  const tourStep = useCallback(
    (_: number, step: TourStep) => {
      if (step.target === 'tab-dossier') setTab('dossier');
      else if (step.target === 'side') setTab(inLab ? 'lab' : 'standards');
    },
    [inLab]
  );

  const closeTour = useCallback((finished: boolean) => {
    markGuideSeen();
    setTour(false);
    setTab((t) => (t === 'dossier' ? (gameRef.current.mode === 'lab' ? 'lab' : 'standards') : t));
    if (finished) voice.push('agnes', 'Kukuku… lesson one: never trust a guide. Trust measurements. Experiment 01 is waiting, Morumotto-kun.');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const newCareer = async () => {
    setCareer(null);
    try {
      if (game.mode === 'lab') {
        const snap = await api.startCareer(true);
        setGame(snap.state);
        setLab(snap.lab);
        setTab('lab');
        voice.push('agnes', `Career ${pad(snap.lab.career)}. A fresh specimen, as sick as ever. Your sparks came with you. Shall we?`);
      } else {
        const s = await api.resetGame();
        setGame(s);
        await refreshSmells();
      }
      setView('training');
      void voice.refreshPrompt();
    } catch {
      toast('bad', 'Could not start a new career.');
    }
  };

  const closeLabPanel = async () => {
    try {
      const snap = await api.closeLabPanel();
      setLab(snap.lab);
      setGame(snap.state);
    } catch {
      /* ignore */
    }
  };

  // ---- Race hooks -----------------------------------------------------------

  const registerAnswer = useCallback((fn: ((i: number) => Promise<QuizAnswerResult>) | null) => {
    quizAnswerRef.current = fn;
  }, []);

  const onCheckpoint = useCallback(
    (q: DerbyQuestion, i: number) => {
      voice.notify(
        `Race checkpoint ${i + 1} of 3! Read the question and its four options aloud, briefly, then wait for the trainer's answer and call answer_quiz. ` +
          `Question: ${q.question} Code on screen: ${q.code.replace(/\n/g, ' / ')} Options: ${q.options.map((o, k) => `${'ABCD'[k]}) ${o}`).join(' | ')}`
      );
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [voice.notify]
  );

  const onRaceFinished = useCallback(
    (place: number, score: number) => {
      voice.notify(
        `The Grand Derby just finished: the trainee placed ${place} with ${score} of 3 checkpoint answers correct. React in character in two sentences.`
      );
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [voice.notify]
  );

  const onCareerComplete = useCallback(
    (summary: CareerSummary) => {
      setCareer(summary);
      setGame(summary.state);
      setLab(summary.lab);
      setView('training');
      void voice.refreshPrompt();
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [voice.refreshPrompt]
  );

  const backToLab = async () => {
    await loadAll();
    void voice.refreshPrompt();
    setView('training');
  };

  const clearCutIn = useCallback(() => setCutIn(null), []);

  // ---- Layout -----------------------------------------------------------

  const exp = lab?.experiment ?? null;
  const review = lab?.review ?? null;
  const activeTab: Tab = tab === 'dossier' ? 'dossier' : inLab ? 'lab' : tab === 'case' ? 'case' : 'standards';
  const wide = activeTab === 'lab' && (!!exp || !!review);

  const stats = (
    <StatsPanel
      state={game}
      lab={lab}
      smells={smells}
      busy={busy}
      flash={flash}
      onTrain={(a) => runAction('train', { attribute: a }, `Train ${STAT_BY_KEY[a].label}`)}
      onExperiment={(c) => runAction('start_experiment', { chapter: c }, `Start experiment ${pad(c)}`)}
      onReview={() => runAction('start_review', {}, 'Start a review')}
      onRest={() => runAction('rest', {}, 'Rest')}
      onRace={() => runAction('start_race', {}, 'Start the Grand Derby')}
      onShowSmells={(a) => {
        setCaseView({ mode: 'list', attribute: a });
        openSide('case');
      }}
    />
  );

  const tabs: { id: Tab; label: string }[] = inLab
    ? [
        { id: 'lab', label: exp && exp.stage !== 'debrief' ? `Experiment ${pad(exp.chapter)}` : review ? 'Pop quiz' : 'Experiments' },
        { id: 'dossier', label: 'Dossier' },
      ]
    : [
        { id: 'standards', label: 'Architecture' },
        { id: 'case', label: 'Case file' },
        { id: 'dossier', label: 'Dossier' },
      ];

  const side = (onClose?: () => void) => (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-stretch bg-ink text-paper">
        {tabs.map((t, i) => (
          <button
            key={t.id}
            data-tour={`tab-${t.id}`}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 font-cond text-[12px] font-bold uppercase tracking-[0.16em] ${
              activeTab === t.id ? 'bg-paper text-ink' : 'text-paper/60 hover:text-acc'
            }`}
          >
            <span className={activeTab === t.id ? 'text-faint' : 'text-paper/30'}>{pad(i + 3)}</span>
            {t.label}
          </button>
        ))}
        <span className="flex-1" />
        {onClose && (
          <button onClick={onClose} className="px-3 font-cond text-[11px] font-bold uppercase tracking-[0.16em] text-paper/60 hover:text-acc">
            Close
          </button>
        )}
      </div>
      <div className="min-h-0 flex-1">
        {activeTab === 'dossier' && lab ? (
          <section className="ef-panel scroll-thin h-full overflow-y-auto">
            <Dossier lab={lab} />
          </section>
        ) : activeTab === 'standards' ? (
          <section className="ef-panel scroll-thin h-full overflow-y-auto">
            <StandardsReport version={reportVersion} lab={lab} onPractice={practiceChapter} onOpenCase={openCaseAt} />
          </section>
        ) : inLab && lab ? (
          review ? (
            <ReviewCard
              review={review}
              concept={lab.mastery.find((m) => m.concept === review.concept)}
              busy={busy}
              voiceLive={voice.live}
              onAnswer={(l) => runAction('answer_review', { option: l }, `Answer ${l}`)}
              onClose={closeLabPanel}
            />
          ) : exp ? (
            <ExperimentBench exp={exp} busy={busy} voiceLive={voice.live} onAction={runAction} onClose={closeLabPanel} />
          ) : (
            <section className="ef-panel scroll-thin h-full overflow-y-auto">
              <LabBoard
                lab={lab}
                busy={busy}
                seasonOver={game.is_game_over}
                onStart={(c) => runAction('start_experiment', { chapter: c }, `Start experiment ${pad(c)}`)}
                onReview={() => runAction('start_review', {}, 'Start a review')}
                onOpenExperiment={() => setTab('lab')}
              />
            </section>
          )
        ) : (
          <CaseFile
            smells={smells}
            view={caseView}
            highlight={highlight}
            busy={busy}
            onView={setCaseView}
            onTrainSmell={(s) => runAction('train', { attribute: s.attribute, smell_id: s.id }, `Drill smell #${s.id}`)}
            onPrescribe={(s) => runAction('write_fix_prescription', { smell_id: s.id }, `Fix prompt for smell #${s.id}`)}
          />
        )}
      </div>
    </div>
  );

  return (
    <div className="relative flex h-full flex-col overflow-hidden bg-ink">
      {/* Backdrop: the lab, desaturated, under a measurement grid */}
      <div className="pointer-events-none absolute inset-0">
        <img
          src={view === 'race' ? '/assets/backgrounds/racetrack.png' : '/assets/backgrounds/training_room.png'}
          alt=""
          className="h-full w-full object-cover opacity-30 grayscale"
        />
        <div className="absolute inset-0 bg-ink/55" />
        <div
          className="absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              'linear-gradient(to right, #f1f1ee 1px, transparent 1px), linear-gradient(to bottom, #f1f1ee 1px, transparent 1px)',
            backgroundSize: '64px 64px',
          }}
        />
        <div className="absolute bottom-3 left-4 font-mono text-[10px] uppercase tracking-[0.2em] text-paper/25">
          tachyon lab // {inLab ? `career ${pad(lab?.career ?? 1)} // day ${lab?.lab_day ?? 1}` : `free lab // ${game.repo_name}`}
        </div>
      </div>

      <TopBar
        state={game}
        lab={lab}
        busy={busy}
        onEnterLab={enterLab}
        onScanRepo={handleScanRepo}
        onRescan={() => runAction('rescan_repo', {}, 'Rescan repository')}
        onToggleStats={() => setDrawer((d) => (d === 'stats' ? null : 'stats'))}
        onToggleCase={() => setDrawer((d) => (d === 'side' ? null : 'side'))}
        onGuide={() => setTour(true)}
      />

      {backendDown && (
        <div className="relative z-20 mx-4 mt-3 flex items-stretch">
          <span className="ef-hazard w-2" />
          <p className="flex-1 bg-paper px-4 py-2 text-sm">
            <b className="font-cond uppercase tracking-[0.1em]">Backend offline.</b> Start it with{' '}
            <code className="font-mono">uvicorn app.main:app --port 8000</code> in <code className="font-mono">backend/</code>.{' '}
            <button className="font-semibold underline" onClick={() => void loadAll()}>
              Retry
            </button>
          </p>
        </div>
      )}

      {view === 'training' ? (
        <main
          className={`relative z-10 grid min-h-0 flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-[288px_minmax(0,1fr)] ${
            wide ? 'xl:grid-cols-[288px_minmax(0,1fr)_minmax(540px,44vw)]' : 'xl:grid-cols-[288px_minmax(0,1fr)_minmax(420px,34vw)]'
          }`}
        >
          <aside className="scroll-thin hidden min-h-0 overflow-y-auto lg:block">{stats}</aside>

          <section className="relative flex min-h-0 flex-col">
            <div className="relative min-h-0 flex-1">
              <AgnesAvatar
                pose={pose}
                mood={game.mood}
                status={voice.status}
                getLevel={() => voice.agentRef.current?.getOutputLevel() ?? 0}
                onPoke={handlePoke}
                flag={exp?.eureka && exp.stage !== 'debrief' ? 'Eureka ×1.5' : null}
              />
            </div>
            <div className="relative z-10 -mt-24" data-tour="dock">
              <VoiceDock voice={voice} onTextFallback={handleTextFallback} textBusy={textBusy || busy} />
            </div>
          </section>

          <aside className="hidden min-h-0 xl:block" data-tour="side">
            {side()}
          </aside>
        </main>
      ) : (
        <main className="relative z-10 min-h-0 flex-1">
          <RaceView
            voiceLive={voice.live}
            onBack={backToLab}
            onCheckpoint={onCheckpoint}
            onFinished={onRaceFinished}
            onCareerComplete={onCareerComplete}
            registerAnswer={registerAnswer}
          />
        </main>
      )}

      {/* Small-screen drawers */}
      {drawer && view === 'training' && (
        <div className="fixed inset-0 z-40 flex justify-end bg-ink/60 xl:hidden" onClick={() => setDrawer(null)}>
          <div className="h-full w-[min(94vw,580px)] animate-slide-in overflow-y-auto p-3" onClick={(e) => e.stopPropagation()}>
            {drawer === 'stats' ? stats : side(() => setDrawer(null))}
          </div>
        </div>
      )}

      <EventLayer cutIn={cutIn} toasts={toasts} onCutInDone={clearCutIn} onToastDone={(id) => setToasts((t) => t.filter((x) => x.id !== id))} />

      {tour && view === 'training' && <Tutorial steps={LAB_TOUR} onStep={tourStep} onClose={closeTour} />}

      {career && <CareerResult summary={career} lab={lab} onNewCareer={newCareer} onClose={() => setCareer(null)} />}
    </div>
  );
};
