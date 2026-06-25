import { useCallback, useRef, useState } from 'react';
import { Loader2, Mic, Square } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
  onSubmit: (audioBase64: string, transcript: string) => void;
  isLoading: boolean;
}

export default function VoiceRecorder({ onSubmit, isLoading }: Props) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState<number>(0);
  const [audioData, setAudioData] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval>>(undefined as unknown as ReturnType<typeof setInterval>);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = reader.result?.toString().split(',')[1] || '';
          setAudioData(base64);
        };
        reader.readAsDataURL(blob);
        stream.getTracks().forEach((t) => t.stop());
      };

      mediaRecorder.start(100);
      setIsRecording(true);
      setRecordingTime(0);

      timerRef.current = setInterval(() => {
        setRecordingTime((t) => t + 1);
      }, 1000);

      setTimeout(() => {
        if (mediaRecorder.state === 'recording') {
          stopRecording();
        }
      }, 60000);
    } catch {
      alert('Microphone access required for voice input');
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    mediaRecorderRef.current?.stop();
    setIsRecording(false);
  }, []);

  const handleSubmit = () => {
    if (audioData) {
      onSubmit(audioData, '');
    }
  };

  const formatTime = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, '0')}`;

  return (
    <div className="flex flex-col items-center gap-6 p-8 rounded-xl border border-slate-200 bg-white">
      <div className="text-center">
        <h3 className="text-lg font-semibold text-slate-900 mb-1">Speak in Hindi or English</h3>
        <p className="text-sm text-slate-500">Describe the job offer you received</p>
      </div>

      {!isRecording && !audioData && (
        <button
          onClick={startRecording}
          className="w-20 h-20 rounded-full bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center shadow-lg shadow-red-200 hover:scale-105 active:scale-95 transition-transform"
        >
          <Mic className="h-8 w-8 text-white" />
        </button>
      )}

      {isRecording && (
        <div className="flex flex-col items-center gap-3">
          <div className="w-20 h-20 rounded-full bg-red-50 border-4 border-red-500 flex items-center justify-center animate-pulse">
            <div className="w-8 h-8 rounded bg-red-500" />
          </div>
          <span className="text-2xl font-mono font-semibold text-red-600">{formatTime(recordingTime)}</span>
          <Button
            variant="outline"
            size="sm"
            onClick={stopRecording}
            className="border-red-300 text-red-600 hover:bg-red-50"
          >
            <Square className="h-4 w-4 mr-1" /> Stop
          </Button>
        </div>
      )}

      {audioData && !isRecording && (
        <div className="flex flex-col items-center gap-3">
          <div className="w-20 h-20 rounded-full bg-green-50 border-4 border-green-500 flex items-center justify-center">
            <Mic className="h-8 w-8 text-green-600" />
          </div>
          <p className="text-sm text-green-600 font-medium">Recording captured</p>
          <div className="flex gap-2">
            <Button
              onClick={handleSubmit}
              disabled={isLoading}
              className="bg-gradient-to-r from-indigo-600 to-violet-600 text-white"
            >
              {isLoading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Investigate
            </Button>
            <Button variant="outline" onClick={() => { setAudioData(null); startRecording(); }}>
              Re-record
            </Button>
          </div>
        </div>
      )}

      <p className="text-xs text-slate-400 text-center max-w-sm">
        Example: "Mujhe ek WhatsApp aaya Wipro ki taraf se, salary 60,000, lekin registration ke liye 3,500 maang rahe hain..."
      </p>
    </div>
  );
}