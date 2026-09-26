import React, { useState, useEffect } from 'react';
import { AttributeType, GameState, AvatarPose } from './types';
import { api } from './services/api';
import { sounds } from './services/audio';
import { VisualNovelStage } from './components/VisualNovelStage';
import { VNTopHUD } from './components/VNTopHUD';
import { AgnesVNSprite } from './components/AgnesVNSprite';
import { VNTrainingMenu } from './components/VNTrainingMenu';
import { VNDialogueBox } from './components/VNDialogueBox';
import { VNRaceTrack } from './components/VNRaceTrack';
import { CommsLogModal, ChatMessage } from './components/CommsLogModal';
import { GameOverModal } from './components/GameOverModal';
import { TrainingAnimationModal } from './components/TrainingAnimationModal';
import confetti from 'canvas-confetti';

const INITIAL_ENGLISH_INTRO =
  "Kukuku… Greetings, Morumotto-kun! I am Dr. Agnes Tachyon, your Chief Enterprise Architect. " +
  "I will guide you through strict enterprise architecture and industry best practices. " +
  "Let our grand software experiment commence!";

const DEFAULT_STATE: GameState = {
  repo_name: 'code-musume',
  turn: 1,
  max_turns: 12,
  energy: 100,
  mood: 'normal',
  attributes: {
    speed: 380,
    stamina: 320,
    power: 410,
    guts: 290,
    wisdom: 450,
  },
  current_pose: 'idle',
  dialogue: INITIAL_ENGLISH_INTRO,
  is_game_over: false,
  interactions_in_cycle: 0,
  interactions_required: 10,
  race_unlocked: false,
};

export const App: React.FC = () => {
  const [state, setState] = useState<GameState>(DEFAULT_STATE);
  const [loading, setLoading] = useState(false);
  const [activeView, setActiveView] = useState<'training' | 'race'>('training');
  const [activeTrainingAttr, setActiveTrainingAttr] = useState<AttributeType | null>(null);

  // Direct Chat & Comms Log State
  const [isSendingChat, setIsSendingChat] = useState(false);
  const [isCommsLogOpen, setIsCommsLogOpen] = useState(false);
  const [chatLog, setChatLog] = useState<ChatMessage[]>([
    {
      id: 'init-1',
      sender: 'agnes',
      text: INITIAL_ENGLISH_INTRO,
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);

  // Load initial game state from FastAPI backend
  useEffect(() => {
    async function loadInitialState() {
      try {
        const fetchedState = await api.getState();
        // Always ensure dialogue is in English if empty
        setState({
          ...fetchedState,
          dialogue: fetchedState.dialogue || INITIAL_ENGLISH_INTRO,
        });
      } catch (err) {
        console.warn('Backend not responding yet, using default state:', err);
      }
    }
    loadInitialState();
  }, []);

  // Handle direct click interaction on Dr. Agnes Tachyon
  const [clickCount, setClickCount] = useState(0);

  const handleAgnesClick = () => {
    sounds.playClick();
    setClickCount((prev) => prev + 1);

    let reactionText = "";
    let reactionPose: AvatarPose = "idle";

    if (state.energy < 25) {
      reactionText = "Zzz… Low cellular energy detected, Morumotto-kun… I require immediate computational caffeine or a mandatory Rest cycle.";
      reactionPose = "tired";
    } else if (state.mood === 'great') {
      reactionText = "Kukuku… Splendid! The synaptic flow is surging at peak frequency! What grand experiment shall we accelerate next?";
      reactionPose = "flow";
    } else {
      const reactions: { text: string; pose: AvatarPose }[] = [
        {
          text: "Kukuku… Are you conducting a tactile sensory analysis on your Chief Enterprise Architect, Morumotto-kun?",
          pose: "thinking",
        },
        {
          text: "Hands off the experimental apparatus! Focus your synaptic energy on refactoring that codebase!",
          pose: "shocked",
        },
        {
          text: "An impromptu architectural audit? Very well. My domain models and interface contracts are immaculate.",
          pose: "serious",
        },
        {
          text: "Hehehe… Such curiosity, Morumotto-kun. Keep up this disciplined rigor and our repository shall transcend all legacy bounds!",
          pose: "happy",
        },
      ];
      const chosen = reactions[clickCount % reactions.length];
      reactionText = chosen.text;
      reactionPose = chosen.pose;
    }

    setState((prev) => ({
      ...prev,
      current_pose: reactionPose,
      dialogue: reactionText,
    }));

    setChatLog((prev) => [
      ...prev,
      {
        id: `interact-${Date.now()}`,
        sender: 'agnes',
        text: reactionText,
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
  };

  // Handle direct transmission / chat message to Dr. Agnes Tachyon
  const handleSendMessage = async (msg: string) => {
    if (isSendingChat || !msg.trim()) return;
    setIsSendingChat(true);

    const now = new Date().toLocaleTimeString();
    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      sender: 'user',
      text: msg,
      timestamp: now,
    };

    setChatLog((prev) => [...prev, userMsg]);

    try {
      const resp = await api.sendDialogue(msg);
      const agnesReply = resp.dialogue || "Kukuku… Fascinating inquiry, Morumotto-kun!";

      const agnesMsg: ChatMessage = {
        id: `agn-${Date.now()}`,
        sender: 'agnes',
        text: agnesReply,
        timestamp: new Date().toLocaleTimeString(),
      };

      setChatLog((prev) => [...prev, agnesMsg]);
      const newInteractions = (resp as any).interactions_in_cycle ?? (state.interactions_in_cycle ?? 0) + 1;
      const isUnlocked = (resp as any).race_unlocked ?? (newInteractions >= (state.interactions_required ?? 10));
      setState((prev) => ({
        ...prev,
        dialogue: agnesReply,
        current_pose: (resp.pose as any) || prev.current_pose,
        interactions_in_cycle: newInteractions,
        race_unlocked: isUnlocked,
      }));
      sounds.playSuccess();
    } catch (err) {
      console.error('Chat dialogue error:', err);
      sounds.playFailure();
    } finally {
      setIsSendingChat(false);
    }
  };

  // Handle Training Turn (Direct execution)
  const handleTrain = async (attr: AttributeType) => {
    if (loading || state.is_game_over || state.energy < 20) return;
    setLoading(true);
    setActiveTrainingAttr(attr);
    sounds.playClick();

    try {
      const result = await api.train(attr);
      setState(result.updated_state);

      // Log training result to comms log with MCP insight if present
      const mcpText = result.mcp_insight ? `\n[MCP RESEARCH]: ${result.mcp_insight}` : '';
      const trainingLog: ChatMessage = {
        id: `train-${Date.now()}`,
        sender: 'agnes',
        text: `[TRAINING REPORT // ${attr.toUpperCase()}]: ${result.tachyon_commentary}${mcpText}`,
        timestamp: new Date().toLocaleTimeString(),
      };
      setChatLog((prev) => [...prev, trainingLog]);

      if (result.success) {
        sounds.playSuccess();
        confetti({
          particleCount: 50,
          spread: 60,
          origin: { y: 0.7 },
        });
      } else {
        sounds.playFailure();
      }
    } catch (err) {
      console.error('Training error:', err);
      sounds.playFailure();
    } finally {
      setLoading(false);
      setActiveTrainingAttr(null);
    }
  };

  // Handle Rest (Direct instant recovery)
  const handleRest = async () => {
    if (loading || state.is_game_over) return;
    setLoading(true);
    sounds.playClick();

    try {
      const result = await api.rest();
      setState(result.updated_state);
      sounds.playSuccess();
      setChatLog((prev) => [
        ...prev,
        {
          id: `rest-${Date.now()}`,
          sender: 'agnes',
          text: `[REST REPORT]: ${result.tachyon_commentary}`,
          timestamp: new Date().toLocaleTimeString(),
        },
      ]);
    } catch (err) {
      console.error('Rest error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Handle Scan Sample Trainee Repo
  const handleScanSampleRepo = async () => {
    if (loading) return;
    setLoading(true);
    sounds.playClick();
    try {
      const newState = await api.scanRepo('sample_trainee_repo');
      setState({
        ...newState,
        dialogue: INITIAL_ENGLISH_INTRO,
      });
      sounds.playSuccess();
    } catch (err) {
      console.error('Scan error:', err);
      sounds.playFailure();
    } finally {
      setLoading(false);
    }
  };

  // Handle Race Navigation
  const handleRace = () => {
    sounds.playClick();
    setActiveView('race');
  };

  const handleBackToTraining = async () => {
    sounds.playClick();
    try {
      const freshState = await api.getState();
      setState((prev) => ({
        ...prev,
        ...freshState,
      }));
    } catch (err) {
      console.warn('Failed to refresh state after race:', err);
    }
    setActiveView('training');
  };

  const handleRestart = async () => {
    sounds.playClick();
    try {
      const newState = await api.scanRepo();
      setState({
        ...newState,
        dialogue: INITIAL_ENGLISH_INTRO,
      });
      setActiveView('training');
    } catch {
      setState({ ...DEFAULT_STATE, turn: 1, energy: 100, is_game_over: false, dialogue: INITIAL_ENGLISH_INTRO });
      setActiveView('training');
    }
  };

  const currentBg =
    activeView === 'race'
      ? '/assets/backgrounds/racetrack.png'
      : '/assets/backgrounds/training_room.png';

  return (
    <div className="w-screen h-screen overflow-hidden bg-[#07090c] flex flex-col justify-between select-none">
      <VisualNovelStage backgroundImage={currentBg} isRace={activeView === 'race'}>
        {activeView === 'training' ? (
          <>
            {/* Top Arknights Endfield Style Tactical HUD */}
            <VNTopHUD
              state={state}
              onScanSampleRepo={handleScanSampleRepo}
              loading={loading}
            />

            {/* Agnes Tachyon Visual Novel Character Sprite */}
            <AgnesVNSprite
              pose={state.current_pose}
              mood={state.mood}
              onClick={handleAgnesClick}
            />

            {/* Tactical Command Console (Trainer Protocols) */}
            <VNTrainingMenu
              energy={state.energy}
              loading={loading}
              onTrain={handleTrain}
              onRest={handleRest}
              onRace={handleRace}
              interactionsInCycle={state.interactions_in_cycle ?? 0}
              interactionsRequired={state.interactions_required ?? 10}
              raceUnlocked={state.race_unlocked ?? false}
            />

            {/* Arknights Endfield Comms Terminal (Dialogue Box with Direct Chat) */}
            <VNDialogueBox
              dialogue={state.dialogue}
              pose={state.current_pose}
              speakerName="DR. AGNES TACHYON"
              onSendMessage={handleSendMessage}
              isSending={isSendingChat}
              onOpenCommsLog={() => setIsCommsLogOpen(true)}
            />
          </>
        ) : (
          /* Widescreen 2D Canvas Racetrack */
          <VNRaceTrack onBackToTraining={handleBackToTraining} />
        )}

        {/* Training Animation / DuckDuckGo MCP Telemetry Modal */}
        {activeTrainingAttr && (
          <TrainingAnimationModal attribute={activeTrainingAttr} />
        )}

        {/* Comms Log / Chat History Modal */}
        {isCommsLogOpen && (
          <CommsLogModal
            messages={chatLog}
            onClose={() => setIsCommsLogOpen(false)}
          />
        )}

        {/* Graduation / Game Over Modal */}
        {state.is_game_over && (
          <GameOverModal state={state} onRestart={handleRestart} />
        )}
      </VisualNovelStage>
    </div>
  );
};
