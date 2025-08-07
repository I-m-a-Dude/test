import { create } from 'zustand';
import type { HistogramData, ProfileCurveData } from '@/types/analysis-types';

interface AnalysisState {
  multiPlanarView: boolean;
  threeDReconstruction: boolean;
  showHistogram: boolean;
  showProfileCurves: boolean;
  isCineMode: boolean;
  // Basic brightness/contrast controls (0-200%)
  brightness: number;
  contrast: number;
  // Professional windowing controls (actual intensity values)
  windowCenter: number;
  windowWidth: number;
  sliceThickness: number;
  histogramData: HistogramData[];
  profileCurveData: ProfileCurveData[];
  showMetadataViewer: boolean;
  metadata: Record<string, any> | null;
  intensityRange: { min: number; max: number };
  useWindowing: boolean; // Toggle between simple and professional controls
  canvasRef: HTMLCanvasElement | null; // Reference to the main canvas for export
  setMultiPlanarView: (value: boolean) => void;
  setThreeDReconstruction: (value: boolean) => void;
  setShowHistogram: (value: boolean) => void;
  setShowProfileCurves: (value: boolean) => void;
  setIsCineMode: (value: boolean) => void;
  setBrightness: (value: number) => void;
  setContrast: (value: number) => void;
  setWindowCenter: (value: number) => void;
  setWindowWidth: (value: number) => void;
  setSliceThickness: (value: number) => void;
  setHistogramData: (data: HistogramData[]) => void;
  setProfileCurveData: (data: ProfileCurveData[]) => void;
  setShowMetadataViewer: (value: boolean) => void;
  setMetadata: (data: Record<string, any> | null) => void;
  setIntensityRange: (range: { min: number; max: number }) => void;
  setUseWindowing: (value: boolean) => void;
  setCanvasRef: (canvas: HTMLCanvasElement | null) => void;
  resetWindowing: () => void;
  resetBrightness: () => void;
}

export const useAnalysisStore = create<AnalysisState>((set, get) => ({
  multiPlanarView: false,
  threeDReconstruction: false,
  showHistogram: false,
  showProfileCurves: false,
  isCineMode: false,
  brightness: 100,
  contrast: 100,
  windowCenter: 0,
  windowWidth: 1,
  sliceThickness: 1,
  histogramData: [],
  profileCurveData: [],
  showMetadataViewer: false,
  metadata: null,
  intensityRange: { min: 0, max: 1 },
  useWindowing: false, // Start with simple controls
  canvasRef: null,
  setMultiPlanarView: (value) => set({ multiPlanarView: value }),
  setThreeDReconstruction: (value) => set({ threeDReconstruction: value }),
  setShowHistogram: (value) => set({ showHistogram: value }),
  setShowProfileCurves: (value) => set({ showProfileCurves: value }),
  setIsCineMode: (value) => set({ isCineMode: value }),
  setBrightness: (value) => set({ brightness: value }),
  setContrast: (value) => set({ contrast: value }),
  setWindowCenter: (value) => set({ windowCenter: value }),
  setWindowWidth: (value) => set({ windowWidth: value }),
  setSliceThickness: (value) => set({ sliceThickness: value }),
  setHistogramData: (data) => set({ histogramData: data }),
  setProfileCurveData: (data) => set({ profileCurveData: data }),
  setShowMetadataViewer: (value) => set({ showMetadataViewer: value }),
  setMetadata: (data) => set({ metadata: data }),
  setIntensityRange: (range) => set({ intensityRange: range }),
  setUseWindowing: (value) => set({ useWindowing: value }),
  setCanvasRef: (canvas) => set({ canvasRef: canvas }),
  resetWindowing: () => {
    const { intensityRange } = get();
    set({
      windowCenter: (intensityRange.min + intensityRange.max) / 2,
      windowWidth: intensityRange.max - intensityRange.min,
    });
  },
  resetBrightness: () => {
    set({
      brightness: 100,
      contrast: 100,
    });
  },
}));