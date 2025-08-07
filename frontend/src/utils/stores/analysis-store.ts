import { create } from 'zustand';
import type { HistogramData, ProfileCurveData } from '@/types/analysis-types';

interface AnalysisState {
  multiPlanarView: boolean;
  threeDReconstruction: boolean;
  showHistogram: boolean;
  showProfileCurves: boolean;
  isCineMode: boolean;
  brightness: number;
  contrast: number;
  sliceThickness: number;
  histogramData: HistogramData[];
  profileCurveData: ProfileCurveData[];
  showMetadataViewer: boolean;
  metadata: Record<string, any> | null;
  setMultiPlanarView: (value: boolean) => void;
  setThreeDReconstruction: (value: boolean) => void;
  setShowHistogram: (value: boolean) => void;
  setShowProfileCurves: (value: boolean) => void;
  setIsCineMode: (value: boolean) => void;
  setBrightness: (value: number) => void;
  setContrast: (value: number) => void;
  setSliceThickness: (value: number) => void;
  setHistogramData: (data: HistogramData[]) => void;
  setProfileCurveData: (data: ProfileCurveData[]) => void;
  setShowMetadataViewer: (value: boolean) => void;
  setMetadata: (data: Record<string, any> | null) => void;
}

export const useAnalysisStore = create<AnalysisState>((set) => ({
  multiPlanarView: false,
  threeDReconstruction: false,
  showHistogram: false,
  showProfileCurves: false,
  isCineMode: false,
  brightness: 100,
  contrast: 100,
  sliceThickness: 1,
  histogramData: [],
  profileCurveData: [],
  showMetadataViewer: false,
  metadata: null,
  setMultiPlanarView: (value) => set({ multiPlanarView: value }),
  setThreeDReconstruction: (value) => set({ threeDReconstruction: value }),
  setShowHistogram: (value) => set({ showHistogram: value }),
  setShowProfileCurves: (value) => set({ showProfileCurves: value }),
  setIsCineMode: (value) => set({ isCineMode: value }),
  setBrightness: (value) => set({ brightness: value }),
  setContrast: (value) => set({ contrast: value }),
  setSliceThickness: (value) => set({ sliceThickness: value }),
  setHistogramData: (data) => set({ histogramData: data }),
  setProfileCurveData: (data) => set({ profileCurveData: data }),
  setShowMetadataViewer: (value) => set({ showMetadataViewer: value }),
  setMetadata: (data) => set({ metadata: data }),
}));
