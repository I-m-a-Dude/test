import { create } from 'zustand';

interface MriState {
  file: File | null;
  setFile: (file: File | null) => void;
}

export const useMriStore = create<MriState>((set) => ({
  file: null,
  setFile: (file) => set({ file }),
}));
