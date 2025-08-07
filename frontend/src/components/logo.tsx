import { BrainCircuit } from 'lucide-react';
import { Link } from 'react-router-dom';

export function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2 text-xl font-bold text-foreground">
      <BrainCircuit className="h-8 w-8 text-primary" />
      <span>MediView</span>
    </Link>
  );
}