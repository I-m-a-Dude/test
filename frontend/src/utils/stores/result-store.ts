import { create } from 'zustand';
import type { InferenceResponse } from '@/utils/api';

interface ResultState {
  // Analysis data
  analysisResult: string | null;
  inferenceResult: InferenceResponse | null;

  // Files for results page ONLY
  originalFile: File | null;
  segmentationFile: File | null;
  isViewingSegmentation: boolean;

  // Results actions
  setAnalysisResult: (
    result: string | null,
    originalFile: File | null,
    segmentationFile?: File | null,
    inferenceResult?: InferenceResponse | null
  ) => void;
  setViewingSegmentation: (viewing: boolean) => void;
  switchToOriginal: () => void;
  switchToSegmentation: () => void;
  clearResults: () => void;
}

export const useResultStore = create<ResultState>((set, get) => ({
  analysisResult: null,
  inferenceResult: null,
  originalFile: null,
  segmentationFile: null,
  isViewingSegmentation: false,

  setAnalysisResult: (result, originalFile, segmentationFile = null, inferenceResult = null) =>
    set({
      analysisResult: result,
      originalFile: originalFile,
      segmentationFile: segmentationFile,
      inferenceResult: inferenceResult,
      isViewingSegmentation: segmentationFile ? true : false, // Auto-switch to segmentation if available
    }),

  setViewingSegmentation: (viewing) => set({ isViewingSegmentation: viewing }),

  switchToOriginal: () => set({ isViewingSegmentation: false }),

  switchToSegmentation: () => set({ isViewingSegmentation: true }),

  clearResults: () =>
    set({
      analysisResult: null,
      inferenceResult: null,
      originalFile: null,
      segmentationFile: null,
      isViewingSegmentation: false,
    })
}));