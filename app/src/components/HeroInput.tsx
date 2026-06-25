import { useState } from 'react';
import { AlertTriangle, Loader2, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
  onSubmit: (rawInput: string, inputType: string) => void;
  isLoading: boolean;
}

const EXAMPLE_INPUT = `Dear Candidate, aapka profile Infosys mein select ho gaya hai. Salary: 45k/month. Registration fee: Rs.2,499 bhejein infosys-careers.in pe. 24 ghante mein respond karein. — HR Team, Infosys Recruitment`;

export default function HeroInput({ onSubmit, isLoading }: Props) {
  const [input, setInput] = useState('');

  const handleSubmit = () => {
    onSubmit(input, 'paste');
  };

  const handleExample = () => {
    setInput(EXAMPLE_INPUT);
  };

  return (
    <div className="space-y-4">
      <div className="relative">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Paste the job offer message here... (WhatsApp, Email, Telegram)"
          className="w-full min-h-[180px] p-4 rounded-xl border border-slate-200 bg-white text-slate-900 placeholder:text-slate-400 resize-y focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-base leading-relaxed"
          maxLength={10000}
          disabled={isLoading}
        />
        <div className="absolute bottom-3 right-3 text-xs text-slate-400">
          {input.length}/10000
        </div>
      </div>

      <div className="flex flex-col sm:flex-row gap-3">
        <Button
          onClick={handleSubmit}
          disabled={isLoading || input.trim().length < 10}
          className="flex-1 h-12 text-base font-semibold bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-700 hover:to-violet-700 text-white shadow-lg shadow-indigo-200"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              Investigating...
            </>
          ) : (
            <>
              <Sparkles className="h-5 w-5 mr-2" />
              Investigate Offer
            </>
          )}
        </Button>
        <Button
          variant="outline"
          onClick={handleExample}
          disabled={isLoading}
          className="h-12 px-4 text-slate-600 border-slate-200 hover:bg-slate-50"
        >
          <AlertTriangle className="h-4 w-4 mr-2" />
          Try Example
        </Button>
      </div>
    </div>
  );
}