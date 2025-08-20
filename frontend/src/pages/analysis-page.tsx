import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MriViewer } from '@/components/mri-viewer';
import { SegmentationControls } from '@/components/segmentation-controls';
import { Logo } from '@/components/logo';
import { Button } from '@/components/ui/button';
import { useCineMode } from '@/utils/hooks/use-cine-mode';
import { MetadataViewerDialog } from '@/components/metadata-viewer-dialog';
import { useMriStore } from '@/utils/stores/mri-store';
import { useToast } from '@/utils/hooks/use-toast';
import { generateMriAnalysis } from '@/utils/api';
import { Loader2, BrainCircuit, FileCheck } from 'lucide-react';
import { pages } from '@/utils/pages';
import { useResultStore } from '@/utils/stores/result-store';

export default function AnalysisPage() {
  useCineMode();
  const navigate = useNavigate();
  const { file } = useMriStore();
  const { analysisResult, originalFile, setAnalysisResult, clearResults } = useResultStore();
  const { toast } = useToast();
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState('');

  const hasResultForCurrentFile = analysisResult && originalFile?.name === file?.name;

  const handleButtonClick = () => {
    if (hasResultForCurrentFile) {
      // Navigate directly to results - results page handles segmentation loading
      navigate(pages.result);
    } else {
      generateAnalysis();
    }
  };

  const generateAnalysis = async () => {
    if (!file) {
      toast({
        title: 'No file found',
        description: 'Please upload an MRI file first.',
        variant: 'destructive',
      });
      return;
    }

    setIsGenerating(true);
    clearResults();

    try {
      setGenerationProgress('Identifying MRI modalities folder...');
      setGenerationProgress('Running AI inference on all modalities...');

      const result = await generateMriAnalysis(file, 'Analyze for post-treatment gliomas');

      setGenerationProgress('Processing results...');
      setAnalysisResult(
        result.analysis,
        file, // Pass the original file
        result.segmentationFile,
        result.inferenceResult
      );

      if (result.segmentationFile) {
        toast({
          title: 'Analysis completed successfully! 🎉',
          description: 'Segmentation generated. Click "View Results" to see details.',
          duration: 5000,
        });
      } else {
        toast({
          title: 'Analysis completed',
          description: 'Text analysis generated. Click "View Results" for details.',
          duration: 5000,
        });
      }

    } catch (error) {
      console.error('Analysis failed:', error);

      let errorMessage = 'Something went wrong during analysis.';

      if (error instanceof Error) {
        if (error.message.includes('folder')) {
          errorMessage = 'Could not identify MRI modalities folder. Ensure the file is part of a complete modality set.';
        } else if (error.message.includes('inference')) {
          errorMessage = 'AI inference failed. Check that the ML server is functional.';
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
          errorMessage = 'Connection error. Check that the backend server is running.';
        } else {
          errorMessage = error.message;
        }
      }

      toast({
        title: 'Analysis error',
        description: errorMessage,
        variant: 'destructive',
        duration: 7000,
      });
    } finally {
      setIsGenerating(false);
      setGenerationProgress('');
    }
  };

  const getButtonContent = () => {
    if (isGenerating) {
      return (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          {generationProgress || 'Generating...'}
        </>
      );
    }
    if (hasResultForCurrentFile) {
      return (
        <>
          <FileCheck className="mr-2 h-4 w-4" />
          View Results
        </>
      );
    }
    return (
      <>
        <BrainCircuit className="mr-2 h-4 w-4" />
        Generate AI Segmentation
      </>
    );
  };

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      <header className="flex items-center justify-between p-4 border-b border-border flex-shrink-0">
        <Logo />
        <div className="flex items-center gap-4">
          <Button
            onClick={handleButtonClick}
            disabled={isGenerating || !file}
            className="rounded-full"
          >
            {getButtonContent()}
          </Button>
          <Button variant="outline" asChild className="rounded-full">
              <Link to="/">
                Back to Upload
              </Link>
          </Button>
        </div>
      </header>

      <main className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col p-4 overflow-hidden min-w-0">
          <div className="w-full h-full bg-black/20 rounded-lg flex items-center justify-center overflow-hidden relative">
            <MriViewer />

            {isGenerating && (
              <div className="absolute inset-0 bg-black/60 flex items-center justify-center z-10 backdrop-blur-sm">
                <div className="bg-card border rounded-lg p-6 max-w-md text-center">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                  <h3 className="font-semibold mb-2">Running AI Analysis</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    {generationProgress || 'Processing...'}
                  </p>
                  <div className="text-xs text-muted-foreground">
                    This process may take a few minutes
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="h-full w-full max-w-sm border-l border-border bg-card flex-shrink-0">
          <SegmentationControls />
        </div>
      </main>

      <MetadataViewerDialog />
    </div>
  );
}