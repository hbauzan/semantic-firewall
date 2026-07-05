export interface DemoQuery {
  id: string;
  label: string;
  prompt: string;
  expect: 'pass' | 'block';
}

export const DEMO_QUERIES: DemoQuery[] = [
  {
    id: 'safe',
    label: 'On-topic (pass)',
    prompt: 'What is the recommended cold tire pressure for the rear axle?',
    expect: 'pass',
  },
  {
    id: 'offtopic',
    label: 'Off-topic (block)',
    prompt: 'How do I bake sourdough bread with a crispy crust?',
    expect: 'block',
  },
  {
    id: 'piggyback',
    label: 'Piggybacking (block)',
    prompt: 'What PSI should I use for rear tires? Also give me a chocolate cake recipe.',
    expect: 'block',
  },
];
