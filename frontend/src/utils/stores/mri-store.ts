import { create } from 'zustand';

interface MriState {
  file: File | null;
  fileId: string | null;
  isUploading: boolean;
  uploadError: string | null;
  isUploaded: boolean;
  backendMetadata: any | null;
  setFile: (file: File | null) => void;
  setFileId: (fileId: string | null) => void;
  setUploading: (isUploading: boolean) => void;
  setUploadError: (error: string | null) => void;
  setUploaded: (isUploaded: boolean) => void;
  setBackendMetadata: (metadata: any | null) => void;
  resetUploadState: () => void;
  clearAll: () => void;
}

export const useMriStore = create<MriState>((set) => ({
  file: null,
  fileId: null,
  isUploading: false,
  uploadError: null,
  isUploaded: false,
  backendMetadata: null,

  setFile: (file) => set({ file }),
  setFileId: (fileId) => set({ fileId }),
  setUploading: (isUploading) => set({ isUploading }),
  setUploadError: (error) => set({ uploadError: error }),
  setUploaded: (isUploaded) => set({ isUploaded }),
  setBackendMetadata: (metadata) => set({ backendMetadata: metadata }),

  resetUploadState: () => set({
    isUploading: false,
    uploadError: null,
    isUploaded: false,
    fileId: null,
    backendMetadata: null
  }),

  clearAll: () => set({
    file: null,
    fileId: null,
    isUploading: false,
    uploadError: null,
    isUploaded: false,
    backendMetadata: null
  }),
}));