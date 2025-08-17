import { useState, type DragEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, File, X, Loader2, CheckCircle, AlertCircle, FolderOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/utils/cn';
import { useToast } from '@/utils/hooks/use-toast';
import { useMriStore } from '@/utils/stores/mri-store';
import { pages } from '@/utils/pages';
import { useResultStore } from '@/utils/stores/result-store';
import { uploadMriFile } from '@/utils/api';

type UploadStatus = 'idle' | 'uploading' | 'success' | 'error';

interface MriUploaderProps {
  onOpenFileManager?: () => void;
}

export function MriUploader({ onOpenFileManager }: MriUploaderProps) {
  const setMriFile = useMriStore((state) => state.setFile);
  const mriFile = useMriStore((state) => state.file);
  const setAnalysisResult = useResultStore((state) => state.setAnalysisResult);

  const [isDragging, setIsDragging] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<UploadStatus>('idle');
  const [uploadProgress, setUploadProgress] = useState(0);

  const navigate = useNavigate();
  const { toast } = useToast();

  const handleFileUpload = async (file: File) => {
    setUploadStatus('uploading');
    setUploadProgress(0);

    try {
      const response = await uploadMriFile(
        file,
        (progress) => setUploadProgress(progress) // Progress callback
      );

      console.log('✅ Upload reușit:', response);

      setUploadStatus('success');
      setUploadProgress(100);

      toast({
        title: 'Upload reușit!',
        description: `Fișierul ${file.name} a fost trimis către server.`,
      });

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
      // Acceptă fișiere .nii, .nii.gz și .zip
      if (selectedFile.name.endsWith('.nii') ||
          selectedFile.name.endsWith('.nii.gz') ||
          selectedFile.name.endsWith('.zip')) {
        setMriFile(selectedFile);
        setAnalysisResult(null, null);

        // Trimite fișierul către backend folosind api.ts
        try {
          await handleFileUpload(selectedFile);
        } catch (error) {
          // Errorurile sunt gestionate în funcția handleFileUpload
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
    setMriFile(null);
    setAnalysisResult(null, null);
    setUploadStatus('idle');
    setUploadProgress(0);
  };

  const handleNavigateToAnalysis = () => {
    if (mriFile) {
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
    switch (uploadStatus) {
      case 'uploading':
        return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />;
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      default:
        return null;
    }
  };

  const getUploadStatusText = () => {
    switch (uploadStatus) {
      case 'uploading':
        return 'Se încarcă pe server...';
      case 'success':
        return 'Încărcat cu succes';
      case 'error':
        return 'Eroare la încărcare';
      default:
        return '';
    }
  };

  return (
    <div className="w-full">
      {!mriFile ? (
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

              {/* Buton pentru fișierele de pe server */}
              {onOpenFileManager && (
                <div className="mt-6">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleOpenFileManager}
                    className="flex items-center gap-2"
                  >
                    <FolderOpen className="h-4 w-4" />
                    Vezi fișierele de pe server
                  </Button>
                </div>
              )}
            </div>
            <input
              id="file-upload"
              type="file"
              className="sr-only"
              accept=".nii,.nii.gz,.zip"
              onChange={(e) => handleFile(e.target.files?.[0])}
              disabled={uploadStatus === 'uploading'}
            />
          </label>
        </div>
      ) : (
        <div className="w-full bg-card border rounded-lg p-6 flex flex-col items-center justify-center gap-4">
          <div className="flex items-center gap-3 bg-muted p-3 rounded-md w-full max-w-md">
            <File className="h-6 w-6 text-primary" />
            <span className="font-mono text-sm truncate flex-1">{mriFile.name}</span>
            <div className="flex items-center gap-2">
              {getUploadStatusIcon()}
              <Button
                variant="ghost"
                size="icon"
                onClick={handleRemoveFile}
                className="h-8 w-8"
                disabled={uploadStatus === 'uploading'}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>

          {/* Status upload */}
          {uploadStatus !== 'idle' && (
            <div className="w-full max-w-md">
              <div className="flex items-center justify-between text-sm mb-2">
                <span className={cn(
                  uploadStatus === 'success' && 'text-green-600',
                  uploadStatus === 'error' && 'text-red-600',
                  uploadStatus === 'uploading' && 'text-blue-600'
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
            disabled={isNavigating || uploadStatus === 'uploading'}
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