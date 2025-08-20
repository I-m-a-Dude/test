import { create } from 'zustand';
import type { ViewAxis } from '@/types/view-types';

interface ResultsViewerState {
  // Current file being viewed in results
  currentFile: File | null;

  // Viewer controls for results page only
  slice: number;
  maxSlices: Record<ViewAxis, number>;
  axis: ViewAxis;
  zoom: number;
  pan: { x: number; y: number };

  // Actions
  setCurrentFile: (file: File | null) => void;
  setSlice: (slice: number | ((prevSlice: number) => number)) => void;
  setAxis: (axis: ViewAxis) => void;
  setMaxSlices: (maxSlices: Record<ViewAxis, number>) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  setPan: (pan: { x: number; y: number }) => void;
  resetView: () => void;
}

export const useResultsViewerStore = create<ResultsViewerState>((set, get) => ({
  currentFile: null,
  slice: 0,
  maxSlices: { axial: 0, sagittal: 0, coronal: 0 },
  axis: 'axial',
  zoom: 1,
  pan: { x: 0, y: 0 },

  setCurrentFile: (file) => set({ currentFile: file }),

  setSlice: (slice) => {
    if (typeof slice === 'function') {
      set((state) => ({ slice: slice(state.slice) }));
    } else {
      set({ slice });
    }
  },

  setAxis: (axis) => {
    const { maxSlices } = get();
    set({ axis, slice: Math.floor(maxSlices[axis] / 2) });
  },

  setMaxSlices: (maxSlices) => {
    const { axis } = get();
    set({ maxSlices, slice: Math.floor(maxSlices[axis] / 2) });
  },

  zoomIn: () => set((state) => ({ zoom: Math.min(state.zoom * 1.2, 10) })),
  zoomOut: () => set((state) => ({ zoom: Math.max(state.zoom / 1.2, 0.1) })),
  setPan: (pan) => set({ pan }),

  resetView: () => {
    const { maxSlices, axis } = get();
    set({ zoom: 1, pan: { x: 0, y: 0 }, slice: Math.floor(maxSlices[axis] / 2) });
  },
}));