import { Logo } from '@/components/logo';
import { MriUploader } from '@/components/mri-uploader';

export default function HomePage() {
  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      <header className="p-4">
        <Logo />
      </header>
      <main className="flex flex-1 flex-col items-center justify-center text-center p-4">
        <div className="w-full max-w-2xl">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4">
            MRI Analysis Platform
          </h1>
          <p className="text-lg text-muted-foreground mb-8 max-w-lg mx-auto">
            Upload your .nii or .nii.gz file to begin instant visualization and
            AI-powered analysis.
          </p>
          <MriUploader />
        </div>
      </main>
      <footer className="p-4 text-center text-sm text-muted-foreground">
        &copy; Made by Tudor Ioan Fărcaș
      </footer>
    </div>
  );
}
