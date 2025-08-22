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

// New interface for inference response
export interface InferenceResponse {
  message: string;
  folder_name: string;
  timing: {
    preprocess_time: number;
    inference_time: number;
    postprocess_time: number;
    total_time: number;
  };
  segmentation_info: {
    shape: number[];
    classes_found: number[];
    class_counts: Record<string, number>;
    total_segmented_voxels: number;
  };
  saved_file: string;
  preprocessing_config: Record<string, never>;
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
 * Run inference on a folder to generate segmentation
 */
export const runInferenceOnFolder = async (folderName: string): Promise<InferenceResponse> => {
  const response = await fetch(`${API_BASE_URL}/inference/folder/${encodeURIComponent(folderName)}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      save_result: true,
      output_filename: null // Use default naming
    })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: 'Eroare la inferență' }));
    throw new Error(errorData.detail || `Eroare HTTP: ${response.status}`);
  }

  return response.json();
};

/**
 * Download segmentation result
 */
export const downloadSegmentationResult = async (folderName: string): Promise<File> => {
  try {
    const response = await fetch(`${API_BASE_URL}/inference/results/${encodeURIComponent(folderName)}/download-segmentation`);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Eroare la descarcarea segmentării' }));
      throw new Error(errorData.detail || `Eroare HTTP: ${response.status}`);
    }

    // Get the blob
    const blob = await response.blob();

    // Create File object for the segmentation
    const segmentationFilename = `${folderName}-seg.nii.gz`;
    const file = new File([blob], segmentationFilename, {
      type: blob.type || 'application/gzip',
      lastModified: Date.now()
    });

    console.log(`[API] Segmentare descărcată: ${segmentationFilename} (${(blob.size / 1024 / 1024).toFixed(2)} MB)`);

    return file;

  } catch (error) {
    console.error('Eroare la descărcarea segmentării:', error);
    throw error;
  }
};

/**
 * Extract folder name from a file path with improved logic and debugging
 */
const extractFolderFromFilePath = async (filename: string): Promise<string | null> => {
  console.log(`🔍 [DEBUG] Trying to extract folder from: "${filename}"`);

  // Method 1: Direct folder path (folder/file.nii.gz)
  if (filename.includes('/')) {
    const folderName = filename.split('/')[0];
    console.log(`✅ [DEBUG] Found folder from path: "${folderName}"`);
    return folderName;
  }

  // Method 2: Extract from common naming patterns
  const commonSuffixes = [
    '_t1n', '_t1c', '_t2w', '_t2f', '_flair',
    '-t1n', '-t1c', '-t2w', '-t2f', '-flair',
    '_T1N', '_T1C', '_T2W', '_T2F', '_FLAIR',
    '-T1N', '-T1C', '-T2W', '-T2F', '-FLAIR',
    '-seg', '_seg', '-segmentation', '_segmentation'
  ];

  const baseName = filename.replace(/\.(nii|nii\.gz)$/i, '');
  console.log(`🔍 [DEBUG] Base name without extension: "${baseName}"`);

  for (const suffix of commonSuffixes) {
    if (baseName.toLowerCase().endsWith(suffix.toLowerCase())) {
      const folderName = baseName.slice(0, -suffix.length);
      console.log(`✅ [DEBUG] Found folder from suffix "${suffix}": "${folderName}"`);
      return folderName;
    }
  }

  // Method 3: Check if this file is part of a folder on the server
  try {
    console.log(`🔍 [DEBUG] Checking server for folders containing this file...`);
    const uploadedFiles = await getUploadedFiles();

    // Look for folders that contain this exact filename
    for (const item of uploadedFiles.items) {
      if (item.type === 'folder' && item.nifti_files?.includes(filename)) {
        console.log(`✅ [DEBUG] Found file in server folder: "${item.name}"`);
        return item.name;
      }

      // Also check if any file in the folder matches the basename
      if (item.type === 'folder' && item.nifti_files) {
        const fileBaseName = filename.replace(/\.(nii|nii\.gz)$/i, '');
        for (const niftiFile of item.nifti_files) {
          const niftiBaseName = niftiFile.replace(/\.(nii|nii\.gz)$/i, '');
          // Check if they share the same base (ignoring modality suffixes)
          if (niftiBaseName.toLowerCase().includes(fileBaseName.toLowerCase()) ||
              fileBaseName.toLowerCase().includes(niftiBaseName.toLowerCase())) {
            console.log(`✅ [DEBUG] Found related file in folder "${item.name}": "${niftiFile}"`);
            return item.name;
          }
        }
      }
    }

    // Method 4: Look for folders with similar names
    const fileBaseName = baseName.toLowerCase();
    for (const item of uploadedFiles.items) {
      if (item.type === 'folder') {
        const folderNameLower = item.name.toLowerCase();
        // Check if folder name is contained in filename or vice versa
        if (fileBaseName.includes(folderNameLower) || folderNameLower.includes(fileBaseName)) {
          console.log(`✅ [DEBUG] Found similar folder name: "${item.name}"`);
          return item.name;
        }
      }
    }

  } catch (error) {
    console.error(`❌ [DEBUG] Error checking server folders:`, error);
  }

  console.log(`❌ [DEBUG] Could not determine folder for file: "${filename}"`);
  console.log(`💡 [DEBUG] Available options:`);
  console.log(`   - Upload a ZIP with all modalities (t1n, t1c, t2w, t2f)`);
  console.log(`   - Ensure file naming follows pattern: "patient_001_t1c.nii.gz"`);
  console.log(`   - Check that file is part of a complete folder on server`);

  return null;
};

/**
 * Enhanced generateMriAnalysis with better error messages
 */
export async function generateMriAnalysis(
  file: File,
  prompt: string
): Promise<{
  analysis: string;
  segmentationFile?: File;
  inferenceResult?: InferenceResponse;
}> {
  console.log('🧠 Starting MRI Analysis for:', file.name);
  console.log('📝 Prompt:', prompt);

  try {
    // Step 1: Extract folder name from current file
    const folderName = await extractFolderFromFilePath(file.name);

    if (!folderName) {
      // Enhanced error message with debugging info
      const uploadedFiles = await getUploadedFiles().catch(() => ({ items: [] }));
      const folders = uploadedFiles.items.filter(item => item.type === 'folder');

      let errorMessage = `Nu s-a putut determina folderul pentru fișierul "${file.name}".

DEBUGGING INFO:
- Nume fișier: "${file.name}"
- Foldere disponibile pe server: ${folders.map(f => f.name).join(', ') || 'Niciun folder'}

SOLUȚII:
1. Asigură-te că ai încărcat un ZIP cu toate modalitățile (t1n, t1c, t2w, t2f)
2. Verifică că fișierul face parte dintr-un folder complet pe server
3. Folosește denumiri standard: "patient_001_t1c.nii.gz"`;

      if (folders.length > 0) {
        errorMessage += `\n\n💡 SUGESTIE: Încearcă să încărci unul din folderele disponibile: ${folders.map(f => f.name).join(', ')}`;
      }

      throw new Error(errorMessage);
    }

    console.log(`📁 Folder detectat: ${folderName}`);

    // Continue with original logic...
    console.log('🔄 Se rulează inferența pe folder...');
    const inferenceResult = await runInferenceOnFolder(folderName);

    console.log('✅ Inferența completă!', {
      timing: inferenceResult.timing,
      classes: inferenceResult.segmentation_info.classes_found,
      savedFile: inferenceResult.saved_file
    });

    console.log('📥 Se descarcă fișierul de segmentare...');
    const segmentationFile = await downloadSegmentationResult(folderName);

    console.log('✅ Segmentare descărcată cu succes!');

    const analysis = generateAnalysisText(inferenceResult, prompt);

    return {
      analysis,
      segmentationFile,
      inferenceResult
    };

  } catch (error) {
    console.error('❌ Eroare la analiza MRI:', error);

    return {
      analysis: `EROARE LA ANALIZA MRI

${error instanceof Error ? error.message : 'Eroare necunoscută'}

Pentru mai multe informații, verifică consola browserului (F12 → Console).`
    };
  }
}

/**
 * Generate human-readable analysis text from inference results
 */
function generateAnalysisText(inferenceResult: InferenceResponse, originalPrompt: string): string {
  const { segmentation_info, timing, folder_name } = inferenceResult;
  
  const totalVoxels = segmentation_info.shape.reduce((a, b) => a * b, 1);
  const segmentedVoxels = segmentation_info.total_segmented_voxels;
  const segmentationPercentage = ((segmentedVoxels / totalVoxels) * 100).toFixed(2);

  // Map class numbers to clinical names
  const classNames: Record<number, string> = {
    0: 'Background',
    1: 'NETC (Non-Enhancing Tumor Core)',
    2: 'SNFH (Surrounding FLAIR Hyperintensity)', 
    3: 'ET (Enhancing Tumor)',
    4: 'RC (Resection Cavity)'
  };

  const foundClasses = segmentation_info.classes_found
    .filter(cls => cls > 0) // Exclude background
    .map(cls => classNames[cls] || `Class ${cls}`)
    .join(', ');

  return `ANALIZĂ AUTOMATĂ MRI - SEGMENTAREA GLIOMELOR POST-TRATAMENT

Dataset analizat: ${folder_name}
Prompt utilizator: "${originalPrompt}"

REZULTATE SEGMENTARE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Statistici generale:
• Dimensiuni volum: ${segmentation_info.shape.join(' × ')} voxeli
• Total voxeli segmentați: ${segmentedVoxels.toLocaleString()} (${segmentationPercentage}% din volum)
• Clase identificate: ${foundClasses || 'Nicio țesut patologic detectat'}

📈 Distribuția țesuturilor:
${Object.entries(segmentation_info.class_counts)
  .filter(([cls]) => parseInt(cls) > 0) // Exclude background
  .map(([cls, count]) => {
    const className = classNames[parseInt(cls)] || `Class ${cls}`;
    const percentage = ((count / totalVoxels) * 100).toFixed(3);
    return `• ${className}: ${count.toLocaleString()} voxeli (${percentage}%)`;
  }).join('\n')}

⏱️ Performanță procesare:
• Preprocesare: ${timing.preprocess_time.toFixed(2)}s
• Inferență model AI: ${timing.inference_time.toFixed(2)}s  
• Postprocesare: ${timing.postprocess_time.toFixed(2)}s
• **Total: ${timing.total_time.toFixed(2)}s**


⚠️ NOTĂ IMPORTANTĂ:
Această analiză este generată automat de un model de inteligență artificială și are scop de asistență în diagnoză. Rezultatele TREBUIE să fie validate de un radiolog calificat înainte de orice decizie clinică.

🔬 Model utilizat: MedNeXt (MONAI) - BraTS 2024
📅 Data analizei: ${new Date().toLocaleString('ro-RO')}`;
}



// Keep all existing functions unchanged...
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

export const fileToDataUrl = (file: File): Promise<string> => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
};