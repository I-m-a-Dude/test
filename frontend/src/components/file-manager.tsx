import { useState, useEffect } from 'react';
import { Download, Trash2, RefreshCw, File, Calendar, HardDrive } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useToast } from '@/utils/hooks/use-toast';
import { getUploadedFiles, downloadFileAttachment, deleteUploadedFile } from '@/utils/api';

interface FileItem {
  filename: string;
  size: number;
  size_mb: string;
  modified: number;
  path: string;
}

interface FilesResponse {
  files: FileItem[];
  count: number;
}

export function FileManager() {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const { toast } = useToast();

  const loadFiles = async () => {
    setLoading(true);
    try {
      const response: FilesResponse = await getUploadedFiles();
      setFiles(response.files);

      if (response.count === 0) {
        toast({
          title: 'Niciun fișier găsit',
          description: 'Nu există fișiere încărcate pe server.',
        });
      }
    } catch (error) {
      console.error('Eroare la încărcarea fișierelor:', error);
      toast({
        title: 'Eroare',
        description: 'Nu s-au putut încărca fișierele de pe server.',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (filename: string) => {
    setDownloading(filename);
    try {
      await downloadFileAttachment(filename);
      toast({
        title: 'Descărcare reușită',
        description: `Fișierul ${filename} a fost descărcat.`,
      });
    } catch (error) {
      console.error('Eroare la descărcare:', error);
      toast({
        title: 'Eroare la descărcare',
        description: error instanceof Error ? error.message : 'Eroare necunoscută.',
        variant: 'destructive',
      });
    } finally {
      setDownloading(null);
    }
  };

  const handleDelete = async (filename: string) => {
    setDeleting(filename);
    try {
      await deleteUploadedFile(filename);
      setFiles(files.filter(file => file.filename !== filename));
      toast({
        title: 'Fișier șters',
        description: `Fișierul ${filename} a fost șters de pe server.`,
      });
    } catch (error) {
      console.error('Eroare la ștergere:', error);
      toast({
        title: 'Eroare la ștergere',
        description: error instanceof Error ? error.message : 'Eroare necunoscută.',
        variant: 'destructive',
      });
    } finally {
      setDeleting(null);
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString('ro-RO');
  };

  useEffect(() => {
    loadFiles();
  }, []);

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="h-5 w-5" />
              Fișiere de pe Server
            </CardTitle>
            <CardDescription>
              Gestionează fișierele MRI încărcate pe server
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={loadFiles}
            disabled={loading}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Reîmprospătează
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="text-center py-8">
            <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
            <p className="text-muted-foreground">Se încarcă fișierele...</p>
          </div>
        ) : files.length === 0 ? (
          <div className="text-center py-8">
            <File className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-lg font-medium">Niciun fișier găsit</p>
            <p className="text-muted-foreground">Nu există fișiere încărcate pe server.</p>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="text-sm text-muted-foreground mb-4">
              {files.length} fișier{files.length !== 1 ? 'e' : ''} găsit{files.length !== 1 ? 'e' : ''}
            </div>
            {files.map((file) => (
              <div
                key={file.filename}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <File className="h-4 w-4 text-primary flex-shrink-0" />
                    <span className="font-medium truncate">{file.filename}</span>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <HardDrive className="h-3 w-3" />
                      {file.size_mb}
                    </span>
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {formatDate(file.modified)}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownload(file.filename)}
                    disabled={downloading === file.filename || deleting === file.filename}
                    className="flex items-center gap-1"
                  >
                    <Download className="h-3 w-3" />
                    {downloading === file.filename ? 'Se descarcă...' : 'Descarcă'}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(file.filename)}
                    disabled={downloading === file.filename || deleting === file.filename}
                    className="flex items-center gap-1 text-destructive hover:text-destructive"
                  >
                    <Trash2 className="h-3 w-3" />
                    {deleting === file.filename ? 'Se șterge...' : 'Șterge'}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}