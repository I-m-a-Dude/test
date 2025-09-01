import { create } from 'zustand';
import type { InferenceResponse } from '@/utils/api';

interface ResultState {
  // Analysis data
  analysisResult: string | null;
  inferenceResult: InferenceResponse | null;

  // Files for results page ONLY
  originalFile: File | null;
  segmentationFile: File | null;

  // Results actions
  setAnalysisResult: (
    result: string | null,
    originalFile: File | null,
    segmentationFile?: File | null,
    inferenceResult?: InferenceResponse | null
  ) => void;
  clearResults: () => void;
}

export const useResultStore = create<ResultState>((set) => ({
  analysisResult: null,
  inferenceResult: null,
  originalFile: null,
  segmentationFile: null,

  setAnalysisResult: (result, originalFile, segmentationFile = null, inferenceResult = null) =>
    set({
      analysisResult: result,
      originalFile: originalFile,
      segmentationFile: segmentationFile,
      inferenceResult: inferenceResult,
    }),

  clearResults: () =>
    set({
      analysisResult: null,
      inferenceResult: null,
      originalFile: null,
      segmentationFile: null,
    }),
}));