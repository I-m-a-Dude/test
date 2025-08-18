// Backend API configuration
const API_BASE_URL = 'http://localhost:8000';

// Types for API responses
export interface UploadResponse {
  message: string;
  file_info: {
    filename: string;
    size: number;
    size_mb: string;
    content_type: string;
    type: 'single_file' | 'zip_extracted' | 'zip_failed';
    path?: string;
    extraction?: {
      extracted_folder: string;
      extracted_path: string;
      total_files: number;
      nifti_files_count: number;
      nifti_files: string[];
      all_files: Array<{
        filename: string;
        original_path: string;
        size: number;
        size_mb: string;
      }>;
    };
    error?: string;
  };
}

export interface ApiError {
  detail: string;
}

/**
 * Upload MRI file to backend
 */
export const uploadMriFile = async (
  file: File,
  onProgress?: (progress: number) => void
): Promise<UploadResponse> => {
  return new Promise((resolve, reject) => {
    const formData = new FormData();
    formData.append('file', file);

    const xhr = new XMLHttpRequest();

    // Track upload progress
    if (onProgress) {
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const progress = Math.round((event.loaded / event.total) * 100);
          onProgress(progress);
        }
      });
    }

    // Handle successful response
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response: UploadResponse = JSON.parse(xhr.responseText);
          resolve(response);
        } catch (error) {
          reject(new Error('Răspuns invalid de la server'));
        }
      } else {
        try {
          const errorResponse: ApiError = JSON.parse(xhr.responseText);
          reject(new Error(errorResponse.detail || `Eroare HTTP: ${xhr.status}`));
        } catch (error) {
          reject(new Error(`Eroare HTTP: ${xhr.status}`));
        }
      }
    });

    // Handle network errors
    xhr.addEventListener('error', () => {
      reject(new Error('Eroare de rețea. Verifică dacă serverul rulează.'));
    });

    // Handle timeout
    xhr.addEventListener('timeout', () => {
      reject(new Error('Timeout - upload-ul a luat prea mult timp.'));
    });

    // Configure and send request
    xhr.timeout = 300000; // 5 minutes timeout
    xhr.open('POST', `${API_BASE_URL}/files/upload-mri`);
    xhr.send(formData);
  });
};

/**
 * Get list of uploaded files
 */
export const getUploadedFiles = async (): Promise<{
  items: Array<{
    name: string;
    type: 'file' | 'folder';
    size: number;
    size_mb: string;
    modified: number;
    path: string;
    extension?: string;
    files_count?: number;
    nifti_count?: number;
    nifti_files?: string[];
  }>;
  total_count: number;
  files_count: number;
  folders_count: number;
}> => {
  const response = await fetch(`${API_BASE_URL}/files/`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Eroare necunoscută' }));
    throw new Error(errorData.detail || `Eroare HTTP: ${response.status}`);
  }

  return response.json();
};

/**
 * Delete uploaded file
 */
export const deleteUploadedFile = async (filename: string): Promise<{ message: string }> => {
  const response = await fetch(`${API_BASE_URL}/files/${encodeURIComponent(filename)}`, {
    method: 'DELETE'
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Eroare necunoscută' }));
    throw new Error(errorData.detail || `Eroare HTTP: ${response.status}`);
  }

  return response.json();
};

/**
 * Download file from backend
 */
export const downloadFile = async (filename: string): Promise<void> => {
  try {
    const response = await fetch(`${API_BASE_URL}/files/${encodeURIComponent(filename)}/download`);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Eroare la descărcare' }));
      throw new Error(errorData.detail || `Eroare HTTP: ${response.status}`);
    }

    // Obține blob-ul fișierului
    const blob = await response.blob();

    // Creează un URL temporar pentru blob
    const url = window.URL.createObjectURL(blob);

    // Creează un link temporar și declanșează descărcarea
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();

    // Curăță
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

  } catch (error) {
    console.error('Eroare la descărcarea fișierului:', error);
    throw error;
  }
};

/**
 * Download file as attachment (forces save dialog)
 */
export const downloadFileAttachment = async (filename: string): Promise<void> => {
  try {
    const response = await fetch(`${API_BASE_URL}/files/${encodeURIComponent(filename)}/download-attachment`);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Eroare la descărcare' }));
      throw new Error(errorData.detail || `Eroare HTTP: ${response.status}`);
    }

    // Obține blob-ul fișierului
    const blob = await response.blob();

    // Creează un URL temporar pentru blob
    const url = window.URL.createObjectURL(blob);

    // Creează un link temporar și declanșează descărcarea
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();

    // Curăță
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);

  } catch (error) {
    console.error('Eroare la descărcarea attachment:', error);
    throw error;
  }
};

/**
 * Get info about a specific file
 */
export const getFileInfo = async (filename: string): Promise<{
  filename: string;
  size: number;
  size_mb: string;
  modified: number;
  created: number;
  path: string;
  extension: string;
}> => {
  const response = await fetch(`${API_BASE_URL}/files/${encodeURIComponent(filename)}/info`);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Eroare necunoscută' }));
    throw new Error(errorData.detail || `Eroare HTTP: ${response.status}`);
  }

  return response.json();
};

export const loadFileForViewing = async (filename: string): Promise<File> => {
  try {
    console.log(`[API] Încarcă fișierul pentru vizualizare: ${filename}`);

    const response = await fetch(`${API_BASE_URL}/files/${encodeURIComponent(filename)}/download`);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Eroare la încărcare' }));
      throw new Error(errorData.detail || `Eroare HTTP: ${response.status}`);
    }

    // Obține blob-ul fișierului
    const blob = await response.blob();

    // Creează un obiect File din blob (nu doar salvează pe disc)
    const file = new File([blob], filename, {
      type: blob.type || 'application/octet-stream',
      lastModified: Date.now()
    });

    console.log(`[API] Fișier încărcat pentru vizualizare: ${filename} (${(blob.size / 1024 / 1024).toFixed(2)} MB)`);

    return file;

  } catch (error) {
    console.error('Eroare la încărcarea fișierului pentru vizualizare:', error);
    throw error;
  }
};

/**
 * Verifică dacă un fișier există pe server (pentru validarea restore-ului)
 */
export const checkFileExists = async (filename: string): Promise<boolean> => {
  try {
    const response = await fetch(`${API_BASE_URL}/files/${encodeURIComponent(filename)}/info`);
    return response.ok;
  } catch (error) {
    console.error('Eroare la verificarea existenței fișierului:', error);
    return false;
  }
};

/**
 * Obține lista fișierelor NIfTI disponibile pe server
 */
export const getAvailableNiftiFiles = async (): Promise<string[]> => {
  try {
    const response = await getUploadedFiles();

    // Filtrează doar fișierele NIfTI
    const niftiFiles = response.items
      .filter(item =>
        item.type === 'file' &&
        (item.name.endsWith('.nii') || item.name.endsWith('.nii.gz'))
      )
      .map(item => item.name);

    return niftiFiles;
  } catch (error) {
    console.error('Eroare la obținerea listei de fișiere NIfTI:', error);
    return [];
  }
};

// This is a placeholder for the actual AI analysis function.
// In a real application, this would make a call to a backend service.
export async function generateMriAnalysis(
  file: File,
  prompt: string
): Promise<{ analysis: string }> {
  console.log('Generating analysis for:', file.name);
  console.log('Prompt:', prompt);

  // Simulate network delay
  await new Promise((resolve) => setTimeout(resolve, 2000));

  // Simulate a successful response
  // In a real implementation, you would handle potential errors from the API.
  return {
    analysis: `This is a simulated AI analysis for the file "${file.name}". The analysis is based on the prompt: "${prompt}". The results indicate a high probability of [simulated finding] in the scanned region. Further investigation by a qualified radiologist is recommended.`,
  };
}

export const fileToDataUrl = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};