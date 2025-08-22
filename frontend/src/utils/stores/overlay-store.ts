// frontend/src/utils/stores/overlay-store.ts
import { create } from 'zustand';

interface OverlayState {
  // Overlay file și metadata
  overlayFile: File | null;
  overlayMetadata: {
    originalFolder?: string;
    createdAt?: string;
    fileSize?: number;
  } | null;

  // Loading states
  isLoadingOverlay: boolean;
  overlayError: string | null;

  // Backend persistence
  lastKnownOverlayFile: string | null;

  // Actions
  setOverlayFile: (file: File | null) => void;
  setOverlayMetadata: (metadata: OverlayState['overlayMetadata']) => void;
  setLoadingOverlay: (loading: boolean) => void;
  setOverlayError: (error: string | null) => void;
  setLastKnownOverlayFile: (filename: string | null) => void;

  // Backend functions
  loadOverlayFromBackend: (filename: string) => Promise<void>;
  downloadOverlayForFolder: (folderName: string) => Promise<void>;
  clearOverlay: () => void;
}

export const useOverlayStore = create<OverlayState>((set, get) => ({
  overlayFile: null,
  overlayMetadata: null,
  isLoadingOverlay: false,
  overlayError: null,
  lastKnownOverlayFile: null,

  setOverlayFile: (file) => set({ overlayFile: file }),
  setOverlayMetadata: (metadata) => set({ overlayMetadata: metadata }),
  setLoadingOverlay: (loading) => set({ isLoadingOverlay: loading }),
  setOverlayError: (error) => set({ overlayError: error }),

  setLastKnownOverlayFile: (filename) => {
    set({ lastKnownOverlayFile: filename });
    // Salvează în localStorage pentru persistență
    if (filename) {
      localStorage.setItem('mediview_last_overlay', filename);
    } else {
      localStorage.removeItem('mediview_last_overlay');
    }
  },

  loadOverlayFromBackend: async (filename: string) => {
    set({ isLoadingOverlay: true, overlayError: null });

    try {
      console.log(`[OVERLAY STORE] Încarcă overlay-ul din backend: ${filename}`);

      // Importă funcția API pentru încărcarea overlay-ului
      const { loadFileForViewing } = await import('@/utils/api');

      // Încarcă fișierul overlay folosind API-ul general
      const file = await loadFileForViewing(filename);

      // Actualizează store-ul
      set({
        overlayFile: file,
        lastKnownOverlayFile: filename,
        overlayMetadata: {
          createdAt: new Date().toISOString(),
          fileSize: file.size,
          originalFolder: filename.replace('-overlay.nii.gz', '')
        },
        isLoadingOverlay: false
      });

      // Salvează în localStorage
      localStorage.setItem('mediview_last_overlay', filename);

      console.log(`[OVERLAY STORE] Overlay încărcat cu succes: ${filename}`);

    } catch (error) {
      console.error('[OVERLAY STORE] Eroare la încărcarea overlay-ului:', error);
      set({
        overlayError: error instanceof Error ? error.message : 'Eroare necunoscută',
        isLoadingOverlay: false
      });
      throw error;
    }
  },

  downloadOverlayForFolder: async (folderName: string) => {
    set({ isLoadingOverlay: true, overlayError: null });

    try {
      console.log(`[OVERLAY STORE] Descarcă overlay pentru folder: ${folderName}`);

      // Importă funcția API specifică pentru overlay
      const { downloadOverlayResult } = await import('@/utils/api');

      // Descarcă overlay-ul pentru acest folder
      const overlayFile = await downloadOverlayResult(folderName);

      // Actualizează store-ul
      set({
        overlayFile: overlayFile,
        lastKnownOverlayFile: `${folderName}-overlay.nii.gz`,
        overlayMetadata: {
          originalFolder: folderName,
          createdAt: new Date().toISOString(),
          fileSize: overlayFile.size
        },
        isLoadingOverlay: false
      });

      // Salvează în localStorage
      localStorage.setItem('mediview_last_overlay', `${folderName}-overlay.nii.gz`);

      console.log(`[OVERLAY STORE] Overlay descărcat cu succes pentru: ${folderName}`);

    } catch (error) {
      console.error('[OVERLAY STORE] Eroare la descărcarea overlay-ului:', error);
      set({
        overlayError: error instanceof Error ? error.message : 'Eroare necunoscută',
        isLoadingOverlay: false
      });
      throw error;
    }
  },

  clearOverlay: () => {
    set({
      overlayFile: null,
      overlayMetadata: null,
      isLoadingOverlay: false,
      overlayError: null,
      lastKnownOverlayFile: null
    });
    // Curăță și localStorage
    localStorage.removeItem('mediview_last_overlay');
    console.log('[OVERLAY STORE] Overlay cleared');
  },
}));