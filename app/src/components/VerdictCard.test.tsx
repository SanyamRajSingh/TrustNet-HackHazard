import { render, screen } from '@testing-library/react';
import VerdictCard from './VerdictCard';

describe('VerdictCard Component', () => {
  const mockResult = {
    id: '123',
    trust_score: 15,
    confidence_score: 90,
    verdict: 'HIGH_RISK',
    verdict_label: 'DO NOT RESPOND',
    verdict_color: '#DC2626',
    entities: { fee_amount: 5000 },
    category_scores: {},
    evidence: [],
    hindi_explanation: 'Testing',
    processing_ms: 120,
    graph_connections: { rings: ['Scam Ring 1'] },
  };

  it('renders verdict label correctly', () => {
    // @ts-ignore
    render(<VerdictCard result={mockResult} />);
    expect(screen.getByText('DO NOT RESPOND')).toBeInTheDocument();
  });

  it('renders fee amount warning if present', () => {
    // @ts-ignore
    render(<VerdictCard result={mockResult} />);
    expect(screen.getByText(/Fee Requested: Rs. 5,000/i)).toBeInTheDocument();
  });
});
