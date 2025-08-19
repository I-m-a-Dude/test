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
  const { file, setFile, setLastKnownBackendFile } = useMriStore();
  const { analysisResult, fileName, segmentationFile, setAnalysisResult, clearResults } = useResultStore();
  const { toast } = useToast();
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationProgress, setGenerationProgress] = useState('');

  const hasResultForCurrentFile = analysisResult && fileName === file?.name;

  const handleButtonClick = () => {
    if (hasResultForCurrentFile) {
      // Load segmentation file before navigating
      if (segmentationFile) {
        setFile(segmentationFile);
        setLastKnownBackendFile(segmentationFile.name);
        toast({
          title: 'Loaded segmentation',
          description: 'The segmentation file has been uploaded for viewing.',
        });
      }
      navigate(pages.result);
    } else {
      generateAnalysis();
    }
  };

  const generateAnalysis = async () => {
    if (!file) {
      toast({
        title: 'Missing file',
        description: 'Please upload an MRI file first.',
        variant: 'destructive',
      });
      return;
    }

    setIsGenerating(true);
    clearResults();

    try {
      // Step 1: Start analysis
      setGenerationProgress('Identifying MRI modalities...');

      // Step 2: Generate analysis (this now includes inference)
      setGenerationProgress('Rolling out AI inference...');
      const result = await generateMriAnalysis(file, 'Analizează pentru gliome post-tratament');

      // Step 3: Store results
      setGenerationProgress('Storing results...');
      setAnalysisResult(
        result.analysis,
        file.name,
        result.segmentationFile,
        result.inferenceResult
      );

      // Step 4: Success feedback
      if (result.segmentationFile) {
        toast({
          title: 'Analysis complete',
          description: `The segmentation has been successfully generated. You can view the results now.`,
          duration: 5000,
        });
      } else {
        toast({
          title: 'Analysis complete',
          description: 'The text analysis has been generated. See the results for details.',
          duration: 5000,
        });
      }

    } catch (error) {
      console.error('Analysis failed:', error);

      // Show specific error messages
      let errorMessage = 'Something went wrong with the generation of the analysis.';

      if (error instanceof Error) {
        if (error.message.includes('folder')) {
          errorMessage = 'The folder with the MRI modalities could not be identified. Make sure that the file is part of a complete set of modalities.';
        } else if (error.message.includes('inference')) {
          errorMessage = 'The AI inference failed. Please check the file and try again.';
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
          errorMessage = 'Connection error. Check that the backend server is running.';
        } else {
          errorMessage = error.message;
        }
      }

      toast({
        title: 'Error Generating Analysis',
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
        Generate Analysis
      </>
    );
  };

  const getButtonVariant = () => {
    if (hasResultForCurrentFile) {
      return 'default'; // Success color for viewing results
    }
    return 'default';
  };

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      <header className="flex items-center justify-between p-4 border-b border-border flex-shrink-0">
        <Logo />
        <div className="flex items-center gap-4">
          <Button
            onClick={handleButtonClick}
            disabled={isGenerating || !file}
            className={`rounded-full ${hasResultForCurrentFile ? 'bg-green-600 hover:bg-green-700' : ''}`}
            variant={getButtonVariant()}
          >
            {getButtonContent()}
          </Button>
          <Button variant="outline" asChild className="rounded-full">
              <Link to="/">
                Back to Home
              </Link>
          </Button>
        </div>
      </header>

      <main className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col p-4 overflow-hidden min-w-0">
          <div className="w-full h-full bg-black/20 rounded-lg flex items-center justify-center overflow-hidden relative">
            <MriViewer />

            {/* Overlay pentru progres când se generează analiza */}
            {isGenerating && (
              <div className="absolute inset-0 bg-black/60 flex items-center justify-center z-10 backdrop-blur-sm">
                <div className="bg-card border rounded-lg p-6 max-w-md text-center">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
                  <h3 className="font-semibold mb-2">Working on processing</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    {generationProgress || 'Generating analysis...'}
                  </p>
                  <div className="text-xs text-muted-foreground">
                    Please wait while the analysis is being generated. This may take a few moments depending on the file size and complexity.
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