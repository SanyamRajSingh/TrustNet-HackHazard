import { useEffect, useRef, useState } from 'react';
import { Activity, Clock, Database, ShieldCheck } from 'lucide-react';

interface StatItem {
  icon: React.ElementType;
  value: number;
  label: string;
  suffix?: string;
  color: string;
}

function AnimatedCounter({ value, suffix = '' }: { value: number; suffix?: string }) {
  const [count, setCount] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const animated = useRef(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !animated.current) {
          animated.current = true;
          const duration = 2000;
          const start = performance.now();
          const animate = (now: number) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            setCount(Math.floor(value * eased));
            if (progress < 1) requestAnimationFrame(animate);
          };
          requestAnimationFrame(animate);
        }
      },
      { threshold: 0.5 }
    );
    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, [value]);

  return (
    <span ref={ref}>
      {count.toLocaleString('en-IN')}{suffix}
    </span>
  );
}

const DEMO_STATS: StatItem[] = [
  { icon: Activity, value: 12847, label: 'Offers Investigated', color: 'text-indigo-600' },
  { icon: ShieldCheck, value: 3421, label: 'Scams Detected', color: 'text-red-600' },
  { icon: Database, value: 892, label: 'Entities on Blockchain', color: 'text-emerald-600' },
  { icon: Clock, value: 8, label: 'Avg. Response Time (sec)', suffix: 's', color: 'text-amber-600' },
];

export default function StatsCounter() {
  return (
    <section className="py-12 bg-white border-y border-slate-100">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
          {DEMO_STATS.map((stat, i) => (
            <div key={i} className="text-center p-4 rounded-xl bg-slate-50/50">
              <stat.icon className={`h-7 w-7 ${stat.color} mx-auto mb-3`} />
              <div className="text-3xl sm:text-4xl font-extrabold text-slate-900 mb-1">
                <AnimatedCounter value={stat.value} suffix={stat.suffix} />
              </div>
              <p className="text-sm text-slate-500">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}