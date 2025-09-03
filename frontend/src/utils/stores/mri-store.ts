// frontend/src/utils/stores/mri-store.ts
import { create } from 'zustand';

interface MriState {
  file: File | null;
  fileId: string | null;
  isUploading: boolean;
  uploadError: string | null;
  isUploaded: boolean;
  backendMetadata: never | null;
  isLoadingFromBackend: boolean;
  lastKnownBackendFile: string | null;

  setFile: (file: File | null) => void;
  setFileId: (fileId: string | null) => void;
  setUploading: (isUploading: boolean) => void;
  setUploadError: (error: string | null) => void;
  setUploaded: (isUploaded: boolean) => void;
  setBackendMetadata: (metadata: never | null) => void;
  setLoadingFromBackend: (loading: boolean) => void;
  setLastKnownBackendFile: (filename: string | null) => void;
  loadFileFromBackend: (filename: string) => Promise<void>;
  restoreFromSession: () => Promise<void>;
  resetUploadState: () => void;
  clearAll: () => void;
}

// Helper function pentru sessionStorage
const saveToSession = (filename: string | null) => {
  if (filename) {
    sessionStorage.setItem('mediview_session', JSON.stringify({
      filename,
      timestamp: Date.now()
    }));
  } else {
    sessionStorage.removeItem('mediview_session');
  }
};

const getFromSession = (): string | null => {
  try {
    const session = sessionStorage.getItem('mediview_session');
    if (session) {
      const { filename } = JSON.parse(session);
      return filename;
    }
  } catch (error) {
    console.error('Error reading session:', error);
    sessionStorage.removeItem('mediview_session');
  }
  return null;
};

export const useMriStore = create<MriState>((set, get) => ({
  file: null,
  fileId: null,
  isUploading: false,
  uploadError: null,
  isUploaded: false,
  backendMetadata: null,
  isLoadingFromBackend: false,
  lastKnownBackendFile: null,

  setFile: (file) => {
    set({ file });
    // Salvează în session când se setează un fișier
    if (file) {
      saveToSession(file.name);
      set({ lastKnownBackendFile: file.name, isUploaded: true });
    } else {
      saveToSession(null);
    }
  },

  setFileId: (fileId) => set({ fileId }),
  setUploading: (isUploading) => set({ isUploading }),
  setUploadError: (error) => set({ uploadError: error }),
  setUploaded: (isUploaded) => set({ isUploaded }),
  setBackendMetadata: (metadata) => set({ backendMetadata: metadata }),
  setLoadingFromBackend: (loading) => set({ isLoadingFromBackend: loading }),

  setLastKnownBackendFile: (filename) => {
    set({ lastKnownBackendFile: filename });
    saveToSession(filename);
  },

  loadFileFromBackend: async (filename: string) => {
    set({ isLoadingFromBackend: true, uploadError: null });

    try {
      console.log(`[STORE] Încarcă fișierul din backend: ${filename}`);

      const { loadFileForViewing } = await import('@/utils/api');
      const file = await loadFileForViewing(filename);

      set({
        file,
        isUploaded: true,
        lastKnownBackendFile: filename,
        isLoadingFromBackend: false
      });

      saveToSession(filename);
      console.log(`[STORE] Fișier încărcat cu succes din backend: ${filename}`);

    } catch (error) {
      console.error('[STORE] Eroare la încărcarea din backend:', error);
      set({
        uploadError: error instanceof Error ? error.message : 'Eroare necunoscută',
        isLoadingFromBackend: false
      });
      throw error;
    }
  },

  // Nouă funcție pentru restore automat
  restoreFromSession: async () => {
    const filename = getFromSession();
    if (filename && !get().file) {
      try {
        await get().loadFileFromBackend(filename);
        console.log('[STORE] Session restored successfully');
      } catch (error) {
        console.error('[STORE] Failed to restore session:', error);
        saveToSession(null); // Curăță session invalid
      }
    }
  },

  resetUploadState: () => set({
    isUploading: false,
    uploadError: null,
    isUploaded: false,
    fileId: null,
    backendMetadata: null,
    isLoadingFromBackend: false
  }),

  clearAll: () => {
    set({
      file: null,
      fileId: null,
      isUploading: false,
      uploadError: null,
      isUploaded: false,
      backendMetadata: null,
      isLoadingFromBackend: false,
      lastKnownBackendFile: null
    });
    saveToSession(null); // Curăță session
  },
}));