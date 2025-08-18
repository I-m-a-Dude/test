import { useState, type DragEvent, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, File, X, Loader2, CheckCircle, AlertCircle, FolderOpen, Download, Brain, Eye } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/utils/cn';
import { useToast } from '@/utils/hooks/use-toast';
import { useMriStore } from '@/utils/stores/mri-store';
import { pages } from '@/utils/pages';
import { useResultStore } from '@/utils/stores/result-store';
import { uploadMriFile, loadFileForViewing, type UploadResponse } from '@/utils/api';

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error' | 'file_selection';

interface MriUploaderProps {
  onOpenFileManager?: () => void;
}

export function MriUploader({ onOpenFileManager }: MriUploaderProps) {
  const {
    file,
    isLoadingFromBackend,
    lastKnownBackendFile,
    setFile,
    setLastKnownBackendFile,
    loadFileFromBackend,
    restoreFromBackend
  } = useMriStore();
  const setAnalysisResult = useResultStore((state) => state.setAnalysisResult);

  const [isDragging, setIsDragging] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(null);
  const [selectedNiftiFile, setSelectedNiftiFile] = useState<string | null>(null);
  const [isLoadingSelectedFile, setIsLoadingSelectedFile] = useState(false);

  const navigate = useNavigate();
  const { toast } = useToast();

  // Auto-restore la prima încărcare
  useEffect(() => {
    const attemptRestore = async () => {
      if (!file && !isLoadingFromBackend) {
        try {
          await restoreFromBackend();
        } catch (error) {
          console.log('[UPLOADER] Restore automată eșuată:', error);
        }
      }
    };

    attemptRestore();
  }, [file, isLoadingFromBackend, restoreFromBackend]);

  const getMriModalityInfo = (filename: string) => {
    const lower = filename.toLowerCase();

    if (lower.includes('t1') && (lower.includes('gd') || lower.includes('c') || lower.includes('contrast'))) {
      return {
        type: 'T1C',
        label: 'T1 with Contrast',
        color: 'bg-red-100 text-red-800 border-red-200'
      };
    } else if (lower.includes('t1')) {
      return {
        type: 'T1N',
        label: 'T1 Native',
        color: 'bg-blue-100 text-blue-800 border-blue-200'
      };
    } else if (lower.includes('t2') && lower.includes('flair') || lower.includes('f')) {
      return {
        type: 'T2F',
        label: 'T2 FLAIR',
        color: 'bg-purple-100 text-purple-800 border-purple-200'
      };
    } else if (lower.includes('t2')) {
      return {
        type: 'T2W',
        label: 'T2 Weighted',
        color: 'bg-green-100 text-green-800 border-green-200'
      };
    }

    return {
      type: 'OTHER',
      label: 'Other MRI',
      description: 'Secvență MRI - tip nedetectat automat',
      color: 'bg-gray-100 text-gray-800 border-gray-200',
      icon: '⚪'
    };
  };

  const handleFileUpload = async (file: File) => {
    setUploadStatus('uploading');
    setUploadProgress(0);
    setUploadResponse(null);

    try {
      const response = await uploadMriFile(
        file,
        (progress) => setUploadProgress(progress)
      );

      console.log('✅ Upload reușit:', response);
      setUploadResponse(response);

      // Verifică dacă este ZIP cu multiple fișiere NIfTI
      if (response.file_info.type === 'zip_extracted' &&
          response.file_info.extraction &&
          response.file_info.extraction.nifti_files_count > 1) {

        setUploadStatus('file_selection');
        toast({
          title: 'ZIP extractat cu succes!',
          description: `Au fost găsite ${response.file_info.extraction.nifti_files_count} fișiere NIfTI. Alege unul pentru vizualizare.`,
        });

      } else {
        // Flux normal pentru fișiere individuale
        setUploadStatus('success');
        setUploadProgress(100);
        setLastKnownBackendFile(file.name);

        toast({
          title: 'Upload reușit!',
          description: `Fișierul ${file.name} a fost trimis către server.`,
        });
      }

      return response;

    } catch (error) {
      console.error('❌ Eroare upload:', error);
      setUploadStatus('error');

      toast({
        title: 'Eroare la upload',
        description: error instanceof Error ? error.message : 'A apărut o eroare necunoscută.',
        variant: 'destructive',
      });

      throw error;
    }
  };

  const handleFile = async (selectedFile: File | undefined | null) => {
    if (selectedFile) {
      if (selectedFile.name.endsWith('.nii') ||
          selectedFile.name.endsWith('.nii.gz') ||
          selectedFile.name.endsWith('.zip')) {
        setFile(selectedFile);
        setAnalysisResult(null, null);

        try {
          await handleFileUpload(selectedFile);
        } catch (error) {
          console.error('Upload failed:', error);
        }
      } else {
        toast({
          title: 'Tip de fișier invalid',
          description: 'Te rog încarcă un fișier .nii, .nii.gz sau .zip.',
          variant: 'destructive',
        });
      }
    }
  };

  const handleNiftiFileSelection = async (filename: string) => {
    setIsLoadingSelectedFile(true);
    setSelectedNiftiFile(filename);

    try {
      // Încarcă fișierul selectat din backend
      const loadedFile = await loadFileForViewing(filename);

      // Actualizează store-ul
      setFile(loadedFile);
      setLastKnownBackendFile(filename);
      setAnalysisResult(null, null);

      toast({
        title: 'Fișier selectat cu succes!',
        description: `${filename} a fost încărcat și este gata pentru analiză.`,
      });

      // Reset upload status to success
      setUploadStatus('success');

    } catch (error) {
      console.error('Error loading selected file:', error);
      toast({
        title: 'Eroare la încărcarea fișierului',
        description: error instanceof Error ? error.message : 'Nu s-a putut încărca fișierul selectat.',
        variant: 'destructive',
      });
    } finally {
      setIsLoadingSelectedFile(false);
    }
  };

  const handleLoadFromBackend = async (filename: string) => {
    try {
      setUploadStatus('uploading');
      await loadFileFromBackend(filename);
      setUploadStatus('success');
      setAnalysisResult(null, null);

      toast({
        title: 'Fișier încărcat!',
        description: `${filename} a fost încărcat din server.`,
      });
    } catch (error) {
      setUploadStatus('error');
      toast({
        title: 'Eroare la încărcare',
        description: error instanceof Error ? error.message : 'Nu s-a putut încărca fișierul.',
        variant: 'destructive',
      });
    }
  };

  const handleDragEnter = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 1) {
      toast({
        title: 'Multiple fișiere nu sunt permise',
        description: 'Te rog încarcă doar un fișier odată.',
        variant: 'destructive',
      });
      return;
    }

    const droppedFile = e.dataTransfer.files[0];
    handleFile(droppedFile);
  };

  const handleRemoveFile = () => {
    setFile(null);
    setLastKnownBackendFile(null);
    setAnalysisResult(null, null);
    setUploadStatus('idle');
    setUploadProgress(0);
    setUploadResponse(null);
    setSelectedNiftiFile(null);
  };

  const handleNavigateToAnalysis = () => {
    if (file) {
      setIsNavigating(true);
      navigate(pages.analysis);
    }
  };

  const handleOpenFileManager = () => {
    if (onOpenFileManager) {
      onOpenFileManager();
    }
  };

  const getUploadStatusIcon = () => {
    if (isLoadingFromBackend) {
      return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
    }

    switch (uploadStatus) {
      case 'uploading':
        return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'file_selection':
        return <Brain className="h-5 w-5 text-purple-500" />;
      default:
        return null;
    }
  };

  const getUploadStatusText = () => {
    if (isLoadingFromBackend) {
      return 'Se încarcă din server...';
    }

    switch (uploadStatus) {
      case 'uploading':
        return 'Se încarcă pe server...';
      case 'success':
        return 'Încărcat cu succes';
      case 'error':
        return 'Eroare la încărcare';
      case 'file_selection':
        return 'Selectează fișierul pentru vizualizare';
      default:
        return '';
    }
  };

  // Loading state pentru restore din backend
  if (isLoadingFromBackend && !file) {
    return (
      <div className="w-full">
        <div className="w-full bg-card border rounded-lg p-6 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">
            Se încarcă ultimul fișier din server...
          </p>
          {lastKnownBackendFile && (
            <p className="text-xs text-muted-foreground">
              {lastKnownBackendFile}
            </p>
          )}
        </div>
      </div>
    );
  }

  // File selection stage pentru ZIP-uri cu multiple fișiere NIfTI
  if (uploadStatus === 'file_selection' && uploadResponse?.file_info.extraction) {
    const extraction = uploadResponse.file_info.extraction;

    return (
      <div className="w-full">
        <Card className="w-full max-w-2xl mx-auto">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-6 w-6 text-primary" />
              Selectează Modalitatea MRI
            </CardTitle>
            <CardDescription>
              Au fost găsite {extraction.nifti_files_count} fișiere NIfTI în arhiva ZIP.
              Alege modalitatea pe care dorești să o vizualizezi.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {extraction.nifti_files.map((filename) => {
                const modalityInfo = getMriModalityInfo(filename);
                const isSelected = selectedNiftiFile === filename;
                const isLoading = isLoadingSelectedFile && isSelected;

                return (
                  <div
                    key={filename}
                    className={cn(
                      "flex items-center justify-between p-4 border rounded-lg transition-all cursor-pointer hover:bg-accent/50",
                      isSelected && "ring-2 ring-primary bg-accent/30"
                    )}
                    onClick={() => !isLoading && handleNiftiFileSelection(filename)}
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className="text-2xl">{modalityInfo.icon}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="font-medium truncate">{filename}</h4>
                          <Badge
                            variant="outline"
                            className={cn("text-xs", modalityInfo.color)}
                          >
                            {modalityInfo.type}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {modalityInfo.description}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {isLoading ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Se încarcă...
                        </div>
                      ) : (
                        <Button variant="outline" size="sm">
                          <Eye className="h-4 w-4 mr-1" />
                          Selectează
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-6 flex justify-center">
              <Button
                variant="outline"
                onClick={handleRemoveFile}
                disabled={isLoadingSelectedFile}
              >
                <X className="h-4 w-4 mr-2" />
                Anulează și încarcă alt fișier
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Upload interface standard
  return (
    <div className="w-full">
      {!file ? (
        <div
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          className="w-full flex justify-center"
        >
          <label
            htmlFor="file-upload"
            className={cn(
              'relative flex flex-col items-center justify-center w-full max-w-lg h-80 rounded-lg border-2 border-dashed border-border bg-card/50 cursor-pointer transition-colors duration-300 group',
              'hover:border-primary/80 hover:bg-accent',
              isDragging && 'border-primary bg-accent'
            )}
          >
            <div className="relative z-10 flex flex-col items-center justify-center text-center p-4">
               <div className={cn(
                  'flex items-center justify-center w-16 h-16 rounded-full bg-background mb-4 border border-border transition-colors duration-300',
                   isDragging ? 'bg-primary/10 border-primary' : 'group-hover:bg-accent group-hover:border-primary/50'
              )}>
                <UploadCloud
                  className={cn(
                    'h-8 w-8 text-muted-foreground transition-colors duration-300',
                    isDragging ? 'text-primary' : 'group-hover:text-primary'
                  )}
                />
              </div>
              <p className="text-lg font-semibold text-foreground">
                {isDragging ? 'Eliberează fișierul aici!' : 'Încarcă scanul MRI'}
              </p>
              <p className="text-muted-foreground text-sm mt-1">
                Drag & drop sau click pentru a selecta un fișier
              </p>
              <p className="text-xs text-muted-foreground mt-4">Fișiere .nii, .nii.gz sau .zip</p>

              <div className="mt-6 flex flex-col gap-2">
                {onOpenFileManager && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleOpenFileManager}
                    className="flex items-center gap-2"
                  >
                    <FolderOpen className="h-4 w-4" />
                    Vezi fișierele de pe server
                  </Button>
                )}

                {lastKnownBackendFile && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleLoadFromBackend(lastKnownBackendFile)}
                    className="flex items-center gap-2"
                    disabled={isLoadingFromBackend}
                  >
                    <Download className="h-4 w-4" />
                    Reîncarcă {lastKnownBackendFile}
                  </Button>
                )}
              </div>
            </div>
            <input
              id="file-upload"
              type="file"
              className="sr-only"
              accept=".nii,.nii.gz,.zip"
              onChange={(e) => handleFile(e.target.files?.[0])}
              disabled={uploadStatus === 'uploading' || isLoadingFromBackend}
            />
          </label>
        </div>
      ) : (
        <div className="w-full bg-card border rounded-lg p-6 flex flex-col items-center justify-center gap-4">
          <div className="flex items-center gap-3 bg-muted p-3 rounded-md w-full max-w-md">
            <File className="h-6 w-6 text-primary" />
            <span className="font-mono text-sm truncate flex-1">{file.name}</span>
            <div className="flex items-center gap-2">
              {getUploadStatusIcon()}
              <Button
                variant="ghost"
                size="icon"
                onClick={handleRemoveFile}
                className="h-8 w-8"
                disabled={uploadStatus === 'uploading' || isLoadingFromBackend}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {(uploadStatus !== 'idle' || isLoadingFromBackend) && (
            <div className="w-full max-w-md">
              <div className="flex items-center justify-between text-sm mb-2">
                <span className={cn(
                  uploadStatus === 'success' && 'text-green-600',
                  uploadStatus === 'error' && 'text-red-600',
                  (uploadStatus === 'uploading' || isLoadingFromBackend) && 'text-blue-600'
                )}>
                  {getUploadStatusText()}
                </span>
                {uploadStatus === 'uploading' && (
                  <span className="text-muted-foreground">{uploadProgress}%</span>
                )}
              </div>
              {uploadStatus === 'uploading' && (
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              )}
            </div>
          )}

          <Button
            onClick={handleNavigateToAnalysis}
            disabled={isNavigating || uploadStatus === 'uploading' || isLoadingFromBackend}
            size="lg"
            className="rounded-full"
          >
            {isNavigating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isNavigating ? 'Se procesează...' : 'Mergi la Analiză'}
          </Button>
        </div>
      )}
    </div>
  );
}