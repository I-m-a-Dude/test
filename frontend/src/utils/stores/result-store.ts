// frontend/src/utils/stores/result-store.ts
import { create } from 'zustand';
import type { InferenceResponse } from '@/utils/api';

interface ResultState {
  // Analysis data
  analysisResult: string | null;
  inferenceResult: InferenceResponse | null;

  // Files for results page
  originalFile: File | null;
  overlayFile: File | null;

  // Results actions
  setAnalysisResult: (
    result: string | null,
    originalFile: File | null,
    overlayFile?: File | null,
    inferenceResult?: InferenceResponse | null
  ) => void;
  restoreFromSession: () => Promise<void>;
  clearResults: () => void;
}

// Helper functions pentru sessionStorage
const saveResultsToSession = (data: {
  analysisResult: string | null;
  inferenceResult: InferenceResponse | null;
  originalFilename: string | null;
  overlayFilename: string | null;
}) => {
  if (data.analysisResult) {
    sessionStorage.setItem('mediview_results', JSON.stringify({
      analysisResult: data.analysisResult,
      inferenceResult: data.inferenceResult,
      originalFilename: data.originalFilename,
      overlayFilename: data.overlayFilename,
      timestamp: Date.now()
    }));
  } else {
    sessionStorage.removeItem('mediview_results');
  }
};

const getResultsFromSession = () => {
  try {
    const session = sessionStorage.getItem('mediview_results');
    if (session) {
      return JSON.parse(session);
    }
  } catch (error) {
    console.error('Error reading results session:', error);
    sessionStorage.removeItem('mediview_results');
  }
  return null;
};

export const useResultStore = create<ResultState>((set, get) => ({
  analysisResult: null,
  inferenceResult: null,
  originalFile: null,
  overlayFile: null,

  setAnalysisResult: (result, originalFile, overlayFile = null, inferenceResult = null) => {
    set({
      analysisResult: result,
      originalFile: originalFile,
      overlayFile: overlayFile,
      inferenceResult: inferenceResult,
    });

    // Salvează în session
    saveResultsToSession({
      analysisResult: result,
      inferenceResult: inferenceResult,
      originalFilename: originalFile?.name || null,
      overlayFilename: overlayFile?.name || null,
    });
  },

  // Nouă funcție pentru restore automat
  restoreFromSession: async () => {
    const sessionData = getResultsFromSession();

    if (sessionData && !get().analysisResult) {
      try {
        console.log('[RESULTS] Restoring from session...');

        // Restaurează datele text
        set({
          analysisResult: sessionData.analysisResult,
          inferenceResult: sessionData.inferenceResult,
        });

        // Încearcă să reîncarce fișierele dacă sunt disponibile
        if (sessionData.overlayFilename || sessionData.originalFilename) {
          const { loadFileForViewing } = await import('@/utils/api');

          let originalFile = null;
          let overlayFile = null;

          try {
            if (sessionData.originalFilename) {
              originalFile = await loadFileForViewing(sessionData.originalFilename);
            }
          } catch (error) {
            console.warn('[RESULTS] Could not restore original file:', error);
          }

          try {
            if (sessionData.overlayFilename) {
              overlayFile = await loadFileForViewing(sessionData.overlayFilename);
            }
          } catch (error) {
            console.warn('[RESULTS] Could not restore overlay file:', error);
          }

          // Actualizează cu fișierele restaurate
          set({ originalFile, overlayFile });
        }

        console.log('[RESULTS] Session restored successfully');
      } catch (error) {
        console.error('[RESULTS] Failed to restore session:', error);
        sessionStorage.removeItem('mediview_results');
      }
    }
  },

  clearResults: () => {
    set({
      analysisResult: null,
      inferenceResult: null,
      originalFile: null,
      overlayFile: null,
    });
    saveResultsToSession({
      analysisResult: null,
      inferenceResult: null,
      originalFilename: null,
      overlayFilename: null,
    });
  },
}));