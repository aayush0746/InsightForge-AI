import React, { useState, useEffect, useRef } from 'react';
import {
  Volume2,
  VolumeX,
  Pause,
  Play,
  RotateCcw,
  FastForward,
  Headphones,
  Sparkles,
  Radio,
  Sliders,
  X,
  Loader2
} from 'lucide-react';
import { api } from '../services/api';

interface AudioBriefingProps {
  text: string;
  title?: string;
  topic?: string;
  className?: string;
}

export const AudioBriefing: React.FC<AudioBriefingProps> = ({
  text,
  title = 'Audio Executive Briefing',
  topic = 'Research Briefing',
  className = '',
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [supported, setSupported] = useState(false);

  // Speed rate (1.0x, 1.25x, 1.5x)
  const [playbackRate, setPlaybackRate] = useState<number>(1.05);

  // Available OS voices
  const [voices, setVoices] = useState<SpeechSynthesisVoice[]>([]);
  const [selectedVoiceUri, setSelectedVoiceUri] = useState<string>('');

  // Podcast Script Generation state
  const [isGeneratingPodcast, setIsGeneratingPodcast] = useState(false);
  const [podcastScript, setPodcastScript] = useState<string | null>(null);
  const [showStudioModal, setShowStudioModal] = useState(false);

  // Current spoken text tracking
  const [activeSpeakingText, setActiveSpeakingText] = useState<string>('');

  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  useEffect(() => {
    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      setSupported(true);

      const loadVoices = () => {
        const available = window.speechSynthesis.getVoices();
        if (available && available.length > 0) {
          setVoices(available);
          // Default to high-quality English voice if available
          const defaultVoice =
            available.find((v) => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Online'))) ||
            available.find((v) => v.lang.startsWith('en')) ||
            available[0];
          if (defaultVoice) {
            setSelectedVoiceUri(defaultVoice.voiceURI);
          }
        }
      };

      loadVoices();
      if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = loadVoices;
      }
    }

    return () => {
      if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  if (!supported || !text) return null;

  const cleanTextForSpeech = (raw: string) => {
    return raw
      .replace(/\[.*?\]/g, '') // Remove [Source 1] citations
      .replace(/[#*`_~]/g, '') // Remove markdown tokens
      .replace(/\|.*?\|/g, '') // Remove tables
      .replace(/https?:\/\/\S+/g, 'link')
      .replace(/\n+/g, '. ')
      .replace(/\s+/g, ' ')
      .trim();
  };

  const handleGeneratePodcastScript = async () => {
    try {
      setIsGeneratingPodcast(true);
      const res = await api.generatePodcastBriefing(text, topic);
      setPodcastScript(res.podcast_script);
      setShowStudioModal(true);
      startPlayback(res.podcast_script);
    } catch (err) {
      console.error('Failed to generate podcast script, falling back to summary:', err);
      startPlayback(text);
    } finally {
      setIsGeneratingPodcast(false);
    }
  };

  const startPlayback = (speechSourceText: string) => {
    if (!('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();
    const cleaned = cleanTextForSpeech(speechSourceText);
    setActiveSpeakingText(cleaned);

    const utterance = new SpeechSynthesisUtterance(cleaned);
    utteranceRef.current = utterance;
    utterance.rate = playbackRate;
    utterance.pitch = 1.0;

    if (selectedVoiceUri && voices.length > 0) {
      const voiceObj = voices.find((v) => v.voiceURI === selectedVoiceUri);
      if (voiceObj) utterance.voice = voiceObj;
    }

    utterance.onend = () => {
      setIsPlaying(false);
      setIsPaused(false);
    };

    utterance.onerror = (e) => {
      console.warn('SpeechSynthesis error:', e);
      setIsPlaying(false);
      setIsPaused(false);
    };

    window.speechSynthesis.speak(utterance);
    setIsPlaying(true);
    setIsPaused(false);
  };

  const handlePlayToggle = () => {
    if (isPaused) {
      window.speechSynthesis.resume();
      setIsPaused(false);
      setIsPlaying(true);
      return;
    }

    if (isPlaying) {
      window.speechSynthesis.pause();
      setIsPaused(true);
      setIsPlaying(false);
      return;
    }

    startPlayback(podcastScript || text);
  };

  const handleStop = () => {
    window.speechSynthesis.cancel();
    setIsPlaying(false);
    setIsPaused(false);
  };

  const handleRateChange = (newRate: number) => {
    setPlaybackRate(newRate);
    if (isPlaying) {
      // Restart at current text with new rate
      startPlayback(activeSpeakingText || podcastScript || text);
    }
  };

  return (
    <>
      {/* Compact Briefing Control Bar */}
      <div
        className={`inline-flex items-center gap-1.5 p-1 rounded-xl bg-indigo-50/80 dark:bg-indigo-950/50 border border-indigo-200/70 dark:border-indigo-800/60 shadow-xs ${className}`}
      >
        <button
          type="button"
          onClick={handlePlayToggle}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition cursor-pointer ${isPlaying
              ? 'bg-amber-600 hover:bg-amber-700 text-white shadow-xs'
              : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs shadow-indigo-600/20'
            }`}
          title={isPlaying ? 'Pause Audio Briefing' : 'Listen to 2-Min Audio Briefing'}
        >
          {isPlaying ? (
            <>
              <Pause className="w-3.5 h-3.5 fill-current" />
              <span>Pause</span>
            </>
          ) : isPaused ? (
            <>
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Resume</span>
            </>
          ) : (
            <>
              <Headphones className="w-3.5 h-3.5" />
              <span>Listen to Briefing</span>
            </>
          )}
        </button>

        {/* Animated Audio Waveform (bounces when active) */}
        {isPlaying && (
          <div className="flex items-center gap-0.5 px-2">
            <span className="w-1 h-3 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.3s]" />
            <span className="w-1 h-4 bg-indigo-600 rounded-full animate-bounce [animation-delay:-0.15s]" />
            <span className="w-1 h-2 bg-indigo-400 rounded-full animate-bounce [animation-delay:-0.4s]" />
            <span className="w-1 h-4 bg-indigo-500 rounded-full animate-bounce [animation-delay:-0.2s]" />
          </div>
        )}

        {(isPlaying || isPaused) && (
          <button
            type="button"
            onClick={handleStop}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800 transition cursor-pointer"
            title="Stop playback"
          >
            <VolumeX className="w-3.5 h-3.5" />
          </button>
        )}

        {/* Speed toggle chip */}
        <div className="flex items-center gap-1 px-1 text-[11px] font-mono text-slate-600 dark:text-slate-300">
          {[1.0, 1.25, 1.5].map((rate) => (
            <button
              key={rate}
              type="button"
              onClick={() => handleRateChange(rate)}
              className={`px-1.5 py-0.5 rounded transition cursor-pointer ${playbackRate === rate
                  ? 'bg-indigo-600 text-white font-bold'
                  : 'hover:bg-indigo-100 dark:hover:bg-indigo-900/60'
                }`}
            >
              {rate}x
            </button>
          ))}
        </div>

        {/* Podcast Studio button */}
        <button
          type="button"
          onClick={handleGeneratePodcastScript}
          disabled={isGeneratingPodcast}
          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-white dark:bg-slate-900 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/80 text-xs font-semibold hover:bg-indigo-50 dark:hover:bg-indigo-950/60 transition cursor-pointer disabled:opacity-50"
          title="Open Podcast Studio for commuting executives & students"
        >
          {isGeneratingPodcast ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-500" />
              <span>Synthesizing...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
              <span>Podcast Studio</span>
            </>
          )}
        </button>
      </div>

      {/* PODCAST STUDIO / COMMUTER BRIEFING MODAL */}
      {showStudioModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in duration-150">
          <div className="flex flex-col w-full max-w-2xl bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
            {/* Header */}
            <div className="relative p-6 bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="p-3 rounded-2xl bg-indigo-500/20 border border-indigo-400/30 text-white">
                  <Radio className="w-6 h-6 text-indigo-300 animate-pulse" />
                </div>
                <div>
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-indigo-500/30 text-indigo-200 text-[10px] font-bold uppercase tracking-wider mb-1">
                    InsightForge Podcast Studio
                  </div>
                  <h3 className="text-lg font-bold text-white">2-Minute Executive Commuter Briefing</h3>
                  <p className="text-xs text-indigo-200/80">{topic}</p>
                </div>
              </div>

              <button
                onClick={() => setShowStudioModal(false)}
                className="p-2 text-indigo-200 hover:text-white rounded-xl hover:bg-white/10 transition cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            <div className="p-6 space-y-6">
              {/* Spoken Script Box */}
              <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-500 font-semibold uppercase tracking-wider">
                  <span>Spoken Host Script</span>
                  <span className="text-indigo-600 dark:text-indigo-400 font-normal">
                    {podcastScript ? `${podcastScript.split(' ').length} words (~2 min)` : 'Standard Briefing'}
                  </span>
                </div>
                <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed max-h-64 overflow-y-auto whitespace-pre-wrap font-sans">
                  {podcastScript || activeSpeakingText || cleanTextForSpeech(text)}
                </p>
              </div>

              {/* Voice & Playback Tuning Controls */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                <div>
                  <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1 uppercase tracking-wider text-[10px]">
                    Speaker Voice
                  </label>
                  <select
                    value={selectedVoiceUri}
                    onChange={(e) => {
                      setSelectedVoiceUri(e.target.value);
                      if (isPlaying) {
                        startPlayback(podcastScript || text);
                      }
                    }}
                    className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-800 dark:text-slate-100 focus:outline-none"
                  >
                    {voices.map((v) => (
                      <option key={v.voiceURI} value={v.voiceURI}>
                        {v.name} ({v.lang})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-slate-600 dark:text-slate-400 font-semibold mb-1 uppercase tracking-wider text-[10px]">
                    Commute Speed Rate
                  </label>
                  <div className="flex gap-2">
                    {[0.8, 1.0, 1.25, 1.5].map((rate) => (
                      <button
                        key={rate}
                        type="button"
                        onClick={() => handleRateChange(rate)}
                        className={`flex-1 py-2 rounded-xl text-xs font-semibold border transition cursor-pointer ${playbackRate === rate
                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                            : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                          }`}
                      >
                        {rate}x
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Master Audio Playbar */}
              <div className="flex items-center justify-between p-4 rounded-2xl bg-indigo-50/60 dark:bg-indigo-950/40 border border-indigo-200/60 dark:border-indigo-900/60">
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={handlePlayToggle}
                    className="w-12 h-12 rounded-2xl bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center shadow-lg shadow-indigo-600/30 transition cursor-pointer"
                  >
                    {isPlaying ? (
                      <Pause className="w-6 h-6 fill-current" />
                    ) : (
                      <Play className="w-6 h-6 fill-current ml-0.5" />
                    )}
                  </button>

                  <div>
                    <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100">
                      {isPlaying ? 'Playing Audio Briefing' : isPaused ? 'Audio Paused' : 'Ready to Stream'}
                    </h4>
                    <p className="text-xs text-slate-500">
                      {isPlaying ? 'Streaming natural TTS to your headphones' : 'Click play to start broadcast'}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => startPlayback(podcastScript || text)}
                    className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-200/50 dark:hover:bg-slate-800 transition cursor-pointer"
                    title="Restart from beginning"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={handleStop}
                    className="p-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-200/50 dark:hover:bg-slate-800 transition cursor-pointer"
                    title="Stop audio"
                  >
                    <VolumeX className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
