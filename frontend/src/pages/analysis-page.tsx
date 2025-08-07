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
import { Loader2 } from 'lucide-react';
import { pages } from '@/utils/pages';
import { useResultStore } from '@/utils/stores/result-store';

export default function AnalysisPage() {
  useCineMode();
  const navigate = useNavigate();
  const { file } = useMriStore();
  const { analysisResult, fileName, setAnalysisResult } = useResultStore();
  const { toast } = useToast();
  const [isGenerating, setIsGenerating] = useState(false);

  const hasResultForCurrentFile = analysisResult && fileName === file?.name;

  const handleButtonClick = () => {
    if (hasResultForCurrentFile) {
      navigate(pages.result);
    } else {
      generateAnalysis();
    }
  };

  const generateAnalysis = async () => {
    if (!file) {
      toast({
        title: 'No file selected',
        description: 'Please upload an MRI file first.',
        variant: 'destructive',
      });
      return;
    }

    setIsGenerating(true);
    setAnalysisResult(null, null);

    try {
      const result = await generateMriAnalysis(file, 'Check for anomalies');
      setAnalysisResult(result.analysis, file.name);
      toast({
        title: 'Analysis Complete',
        description: 'You can now view the result.',
      });
    } catch (error) {
      console.error('Analysis failed:', error);
      toast({
        title: 'Analysis Failed',
        description:
          'Something went wrong while generating the analysis. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const getButtonContent = () => {
    if (isGenerating) {
      return (
        <>
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          Generating...
        </>
      );
    }
    if (hasResultForCurrentFile) {
      return 'View Result';
    }
    return 'Generate Result';
  };

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      <header className="flex items-center justify-between p-4 border-b border-border flex-shrink-0">
        <Logo />
        <div className="flex items-center gap-4">
          <Button onClick={handleButtonClick} disabled={isGenerating} className="rounded-full">
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