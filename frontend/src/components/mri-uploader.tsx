import { useState, type DragEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadCloud, File, X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/utils/cn';
import { useToast } from '@/utils/hooks/use-toast';
import { useMriStore } from '@/utils/stores/mri-store';
import { pages } from '@/utils/pages';
import { useResultStore } from '@/utils/stores/result-store';

export function MriUploader() {
  const setMriFile = useMriStore((state) => state.setFile);
  const mriFile = useMriStore((state) => state.file);
  const setAnalysisResult = useResultStore((state) => state.setAnalysisResult);
  
  const [isDragging, setIsDragging] = useState(false);
  const [isNavigating, setIsNavigating] = useState(false);
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleFile = (selectedFile: File | undefined | null) => {
    if (selectedFile) {
      if (selectedFile.name.endsWith('.nii') || selectedFile.name.endsWith('.nii.gz')) {
        setMriFile(selectedFile);
        // Clear any previous analysis result when a new file is uploaded
        setAnalysisResult(null, null);
      } else {
        toast({
          title: 'Invalid File Type',
          description: 'Please upload a .nii or .nii.gz file.',
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
        title: 'Multiple Files Not Allowed',
        description: 'Please upload only one file at a time.',
        variant: 'destructive',
      });
      return;
    }

    const droppedFile = e.dataTransfer.files[0];
    handleFile(droppedFile);
  };

  const handleRemoveFile = () => {
    setMriFile(null);
    // Clear any previous analysis result when the file is removed
    setAnalysisResult(null, null);
  };

  const handleNavigateToAnalysis = () => {
    if (mriFile) {
      setIsNavigating(true);
      navigate(pages.analysis);
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
                {isDragging ? 'Drop your file here!' : 'Upload MRI Scan'}
              </p>
              <p className="text-muted-foreground text-sm mt-1">
                Drag & drop or click to select a file
              </p>
              <p className="text-xs text-muted-foreground mt-4">.nii or .nii.gz files only</p>
            </div>
            <input
              id="file-upload"
              type="file"
              className="sr-only"
              accept=".nii,.nii.gz"
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
          </label>
        </div>
      ) : (
        <div className="w-full bg-card border rounded-lg p-6 flex flex-col items-center justify-center gap-4">
          <div className="flex items-center gap-3 bg-muted p-3 rounded-md w-full max-w-md">
            <File className="h-6 w-6 text-primary" />
            <span className="font-mono text-sm truncate flex-1">{mriFile.name}</span>
            <Button variant="ghost" size="icon" onClick={handleRemoveFile} className="h-8 w-8">
              <X className="h-4 w-4" />
            </Button>
          </div>
          <Button onClick={handleNavigateToAnalysis} disabled={isNavigating} size="lg" className="rounded-full">
            {isNavigating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isNavigating ? 'Processing...' : 'Go to Analysis'}
          </Button>
        </div>
      )}
    </div>
  );
}