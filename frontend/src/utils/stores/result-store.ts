import { create } from 'zustand';
import type { InferenceResponse } from '@/utils/api';

interface ResultState {
  analysisResult: string | null;
  fileName: string | null;
  segmentationFile: File | null;
  inferenceResult: InferenceResponse | null;
  setAnalysisResult: (
    result: string | null,
    fileName: string | null,
    segmentationFile?: File | null,
    inferenceResult?: InferenceResponse | null
  ) => void;
  clearResults: () => void;
}

export const useResultStore = create<ResultState>((set) => ({
  analysisResult: null,
  fileName: null,
  segmentationFile: null,
  inferenceResult: null,

  setAnalysisResult: (result, fileName, segmentationFile = null, inferenceResult = null) =>
    set({
      analysisResult: result,
      fileName: fileName,
      segmentationFile: segmentationFile,
      inferenceResult: inferenceResult
    }),

  clearResults: () =>
    set({
      analysisResult: null,
      fileName: null,
      segmentationFile: null,
      inferenceResult: null
    })
}));