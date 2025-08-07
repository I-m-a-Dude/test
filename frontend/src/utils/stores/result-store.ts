import { create } from 'zustand';

interface ResultState {
  analysisResult: string | null;
  fileName: string | null;
  setAnalysisResult: (result: string | null, fileName: string | null) => void;
}

export const useResultStore = create<ResultState>((set) => ({
  analysisResult: null,
  fileName: null,
  setAnalysisResult: (result, fileName) => set({ analysisResult: result, fileName: fileName }),
}));
