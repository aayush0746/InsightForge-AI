import React, { useState, useEffect, useRef } from 'react';
import { Mic, MicOff, Radio, Volume2 } from 'lucide-react';

interface VoiceInputButtonProps {
  onTranscript: (text: string) => void;
  disabled?: boolean;
  className?: string;
}

export const VoiceInputButton: React.FC<VoiceInputButtonProps> = ({
  onTranscript,
  disabled = false,
  className = '',
}) => {
  const [isListening, setIsListening] = useState(false);
  const [supported, setSupported] = useState(false);
  const [interimText, setInterimText] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    if (
      typeof window !== 'undefined' &&
      ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)
    ) {
      setSupported(true);
    }
  }, []);

  const stopListening = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (err) {
        // ignore
      }
    }
    setIsListening(false);
    setInterimText('');
  };

  const startListening = () => {
    if (disabled) return;
    setErrorMessage(null);

    try {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      const recognition = new SpeechRecognition();
      recognitionRef.current = recognition;

      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        setIsListening(true);
        setInterimText('');
      };

      recognition.onresult = (event: any) => {
        let finalChunk = '';
        let currentInterim = '';

        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalChunk += event.results[i][0].transcript;
          } else {
            currentInterim += event.results[i][0].transcript;
          }
        }

        if (finalChunk.trim()) {
          onTranscript(finalChunk.trim());
        }
        setInterimText(currentInterim);
      };

      recognition.onerror = (event: any) => {
        console.warn('SpeechRecognition error:', event.error);
        if (event.error === 'not-allowed') {
          setErrorMessage('Microphone access denied. Please allow microphone permissions.');
        } else if (event.error === 'network') {
          setErrorMessage('Network error during speech recognition.');
        }
        stopListening();
      };

      recognition.onend = () => {
        setIsListening(false);
        setInterimText('');
      };

      recognition.start();
    } catch (err: any) {
      console.error('Failed to start speech recognition:', err);
      setErrorMessage('Speech recognition is not available in this browser.');
      setIsListening(false);
    }
  };

  const toggleListening = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  if (!supported) {
    return (
      <button
        type="button"
        disabled
        className="p-2 rounded-xl text-slate-300 dark:text-slate-600 cursor-not-allowed opacity-60"
        title="Speech-to-Text requires Chrome, Edge, or a Web Speech-compatible browser"
      >
        <MicOff className="w-4 h-4" />
      </button>
    );
  }

  return (
    <div className="relative inline-flex items-center">
      <button
        type="button"
        onClick={toggleListening}
        disabled={disabled}
        className={`relative p-2.5 rounded-xl transition duration-200 flex items-center justify-center cursor-pointer ${isListening
            ? 'bg-rose-600 text-white shadow-lg shadow-rose-500/30 scale-105'
            : 'text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-slate-100 dark:hover:bg-slate-800'
          } ${className}`}
        title={isListening ? 'Click to stop listening' : 'Dictate your question with Speech-to-Text'}
      >
        {isListening ? (
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-white" />
            </span>
            <Mic className="w-4 h-4 text-white" />
          </div>
        ) : (
          <Mic className="w-4 h-4" />
        )}
      </button>

      {/* Floating Listening Indicator & Live Transcript Tooltip */}
      {isListening && (
        <div className="absolute right-0 bottom-full mb-2 z-50 flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900/95 dark:bg-slate-800/95 text-white text-xs backdrop-blur-md shadow-xl border border-slate-700 whitespace-nowrap animate-in fade-in zoom-in-95">
          <Radio className="w-3.5 h-3.5 text-rose-400 animate-pulse" />
          <span className="font-semibold text-rose-300">Listening...</span>
          {interimText && (
            <span className="text-slate-300 max-w-[180px] truncate italic">"{interimText}"</span>
          )}
          <span className="text-[10px] text-slate-400 ml-1">Click mic to finish</span>
        </div>
      )}

      {errorMessage && (
        <div className="absolute right-0 bottom-full mb-2 z-50 p-2.5 rounded-xl bg-rose-950 text-rose-200 text-xs border border-rose-800 shadow-xl max-w-xs animate-in fade-in">
          {errorMessage}
        </div>
      )}
    </div>
  );
};
