// frontend/src/utils/stores/mri-store.ts
import { create } from 'zustand';

interface MriState {
  file: File | null;
  fileId: string | null;
  isUploading: boolean;
  uploadError: string | null;
  isUploaded: boolean;
  backendMetadata: never | null;
  // Noi pentru persistență
  isLoadingFromBackend: boolean;
  lastKnownBackendFile: string | null;
  
  setFile: (file: File | null) => void;
  setFileId: (fileId: string | null) => void;
  setUploading: (isUploading: boolean) => void;
  setUploadError: (error: string | null) => void;
  setUploaded: (isUploaded: boolean) => void;
  setBackendMetadata: (metadata: never | null) => void;
  // Noi funcții
  setLoadingFromBackend: (loading: boolean) => void;
  setLastKnownBackendFile: (filename: string | null) => void;
  loadFileFromBackend: (filename: string) => Promise<void>;
  resetUploadState: () => void;
  clearAll: () => void;
}

export const useMriStore = create<MriState>((set, get) => ({
  file: null,
  fileId: null,
  isUploading: false,
  uploadError: null,
  isUploaded: false,
  backendMetadata: null,
  isLoadingFromBackend: false,
  lastKnownBackendFile: null,

  setFile: (file) => set({ file }),
  setFileId: (fileId) => set({ fileId }),
  setUploading: (isUploading) => set({ isUploading }),
  setUploadError: (error) => set({ uploadError: error }),
  setUploaded: (isUploaded) => set({ isUploaded }),
  setBackendMetadata: (metadata) => set({ backendMetadata: metadata }),
  setLoadingFromBackend: (loading) => set({ isLoadingFromBackend: loading }),
  
  setLastKnownBackendFile: (filename) => {
    set({ lastKnownBackendFile: filename });
    // Salvează în localStorage pentru persistență
    if (filename) {
      localStorage.setItem('mediview_last_file', filename);
    } else {
      localStorage.removeItem('mediview_last_file');
    }
  },

  loadFileFromBackend: async (filename: string) => {
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const state = get();
    set({ isLoadingFromBackend: true, uploadError: null });

    try {
      console.log(`[STORE] Încarcă fișierul din backend: ${filename}`);
      
      // Importă funcția API pentru încărcarea în viewer
      const { loadFileForViewing } = await import('@/utils/api');
      
      // Încarcă fișierul folosind API-ul dedicat
      const file = await loadFileForViewing(filename);

      // Actualizează store-ul
      set({ 
        file, 
        isUploaded: true, 
        lastKnownBackendFile: filename,
        isLoadingFromBackend: false 
      });

      // Salvează în localStorage
      localStorage.setItem('mediview_last_file', filename);
      
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
    // Curăță și localStorage
    localStorage.removeItem('mediview_last_file');
  },
}));