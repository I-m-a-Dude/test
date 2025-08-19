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
          title: 'Segmentare încărcată',
          description: 'Fișierul de segmentare a fost încărcat pentru vizualizare.',
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
        title: 'Fișier lipsă',
        description: 'Te rog să încarci mai întâi un fișier MRI.',
        variant: 'destructive',
      });
      return;
    }

    setIsGenerating(true);
    clearResults();

    try {
      // Step 1: Start analysis
      setGenerationProgress('Se identifică folderul cu modalitățile MRI...');

      // Step 2: Generate analysis (this now includes inference)
      setGenerationProgress('Se rulează inferența AI pe toate modalitățile...');
      const result = await generateMriAnalysis(file, 'Analizează pentru gliome post-tratament');

      // Step 3: Store results
      setGenerationProgress('Se procesează rezultatele...');
      setAnalysisResult(
        result.analysis,
        file.name,
        result.segmentationFile,
        result.inferenceResult
      );

      // Step 4: Success feedback
      if (result.segmentationFile) {
        toast({
          title: 'Analiză completă cu succes! 🎉',
          description: `Segmentarea a fost generată cu succes. Poți vizualiza rezultatele acum.`,
          duration: 5000,
        });
      } else {
        toast({
          title: 'Analiză completă',
          description: 'Analiza text a fost generată. Vezi rezultatele pentru detalii.',
          duration: 5000,
        });
      }

    } catch (error) {
      console.error('Analysis failed:', error);

      // Show specific error messages
      let errorMessage = 'Ceva nu a mers bine la generarea analizei.';

      if (error instanceof Error) {
        if (error.message.includes('folder')) {
          errorMessage = 'Nu s-a putut identifica folderul cu modalitățile MRI. Asigură-te că fișierul face parte dintr-un set complet de modalități.';
        } else if (error.message.includes('inference')) {
          errorMessage = 'Inferența AI a eșuat. Verifică că serverul ML este funcțional.';
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
          errorMessage = 'Eroare de conexiune. Verifică că serverul backend rulează.';
        } else {
          errorMessage = error.message;
        }
      }

      toast({
        title: 'Eroare la analiză',
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
          {generationProgress || 'Se generează...'}
        </>
      );
    }
    if (hasResultForCurrentFile) {
      return (
        <>
          <FileCheck className="mr-2 h-4 w-4" />
          Vizualizează Segmentarea
        </>
      );
    }
    return (
      <>
        <BrainCircuit className="mr-2 h-4 w-4" />
        Generează Segmentare AI
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
                Înapoi la Upload
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
                  <h3 className="font-semibold mb-2">Rulează Analiza AI</h3>
                  <p className="text-sm text-muted-foreground mb-4">
                    {generationProgress || 'Se procesează...'}
                  </p>
                  <div className="text-xs text-muted-foreground">
                    Acest proces poate dura câteva minute
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