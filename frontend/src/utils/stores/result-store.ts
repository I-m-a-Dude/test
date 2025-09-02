// frontend/src/utils/stores/result-store.ts
import { create } from 'zustand';
import type { InferenceResponse } from '@/utils/api';

interface ResultState {
  // Analysis data
  analysisResult: string | null;
  inferenceResult: InferenceResponse | null;

  // Files for results page - DOAR overlay-ul
  originalFile: File | null; // Păstrat pentru referință în analysis text
  overlayFile: File | null;  // Fișierul care se afișează în results

  // Results actions
  setAnalysisResult: (
    result: string | null,
    originalFile: File | null,
    overlayFile?: File | null,
    inferenceResult?: InferenceResponse | null
  ) => void;
  clearResults: () => void;
}

export const useResultStore = create<ResultState>((set) => ({
  analysisResult: null,
  inferenceResult: null,
  originalFile: null,
  overlayFile: null,

  setAnalysisResult: (result, originalFile, overlayFile = null, inferenceResult = null) =>
    set({
      analysisResult: result,
      originalFile: originalFile,
      overlayFile: overlayFile,
      inferenceResult: inferenceResult,
    }),

  clearResults: () =>
    set({
      analysisResult: null,
      inferenceResult: null,
      originalFile: null,
      overlayFile: null,
    }),
}));