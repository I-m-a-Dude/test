import { useState } from 'react';
import { FolderOpen } from 'lucide-react';
import { Logo } from '@/components/logo';
import { MriUploader } from '@/components/mri-uploader';
import { FileManager } from '@/components/file-manager';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

export default function HomePage() {
  const [fileManagerOpen, setFileManagerOpen] = useState(false);

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground">
      <header className="p-4">
        <Logo />
      </header>
      <main className="flex flex-1 flex-col items-center justify-center text-center p-4">
        <div className="w-full max-w-2xl">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            MRI Analysis Platform
          </h1>
          <p className="text-lg text-muted-foreground mb-8 max-w-lg mx-auto">
            Upload your .nii, .nii.gz files or .zip archives containing NIfTI files to begin instant visualization and AI-powered analysis.
          </p>
          <MriUploader onOpenFileManager={() => setFileManagerOpen(true)} />
        </div>

        {/* File Manager Dialog */}
        <Dialog open={fileManagerOpen} onOpenChange={setFileManagerOpen}>
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden p-0">
            <DialogHeader className="p-6 pb-0">
              <DialogTitle className="flex items-center gap-2">
                <FolderOpen className="h-5 w-5" />
                Gestionarea fișierelor MRI
              </DialogTitle>
              <DialogDescription>
                Descarcă, șterge sau vizualizează informațiile despre fișierele încărcate pe server.
              </DialogDescription>
            </DialogHeader>
            <div className="p-6 pt-0 overflow-auto">
              <FileManager />
            </div>
          </DialogContent>
        </Dialog>
      </main>
      <footer className="p-4 text-center text-sm text-muted-foreground">
        &copy; Made by Tudor Ioan Fărcaș
      </footer>
    </div>
  );
}