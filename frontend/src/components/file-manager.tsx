import { useState, useEffect } from 'react';
import { Download, Trash2, RefreshCw, File, Calendar, HardDrive, Folder, FileArchive, CheckCircle, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/utils/hooks/use-toast';
import { getUploadedFiles, downloadFileAttachment, deleteUploadedFile } from '@/utils/api';

interface FileItem {
  name: string;
  type: 'file' | 'folder';
  size: number;
  size_mb: string;
  modified: number;
  path: string;
  extension?: string;
  files_count?: number;
  nifti_count?: number;
  nifti_files?: string[];
  segmentation_ready?: boolean;
  found_modalities?: string[];
  missing_modalities?: string[];
}

interface FilesResponse {
  items: FileItem[];
  total_count: number;
  files_count: number;
  folders_count: number;
}

export function FileManager() {
  const [items, setItems] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const { toast } = useToast();

  const loadFiles = async () => {
    setLoading(true);
    try {
      const response: FilesResponse = await getUploadedFiles();
      setItems(response.items);

      if (response.total_count === 0) {
        toast({
          title: 'Niciun element găsit',
          description: 'Nu există fișiere sau foldere pe server.',
          duration: 3000,
        });
      }
    } catch (error) {
      console.error('Eroare la încărcarea elementelor:', error);
      toast({
        title: 'Eroare',
        description: 'Nu s-au putut încărca elementele de pe server.',
        variant: 'destructive',
        duration: 3000,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (itemName: string) => {
    setDownloading(itemName);
    try {
      await downloadFileAttachment(itemName);
      toast({
        title: 'Descărcare reușită',
        description: `${itemName} a fost descărcat.`,
        duration: 3000,
      });
    } catch (error) {
      console.error('Eroare la descărcare:', error);
      toast({
        title: 'Eroare la descărcare',
        description: error instanceof Error ? error.message : 'Eroare necunoscută.',
        variant: 'destructive',
        duration: 3000,
      });
    } finally {
      setDownloading(null);
    }
  };

  const handleDelete = async (itemName: string) => {
    setDeleting(itemName);
    try {
      await deleteUploadedFile(itemName);
      setItems(items.filter(item => item.name !== itemName));
      toast({
        title: 'Element șters',
        description: `${itemName} a fost șters de pe server.`,
        duration: 3000,
      });
    } catch (error) {
      console.error('Eroare la ștergere:', error);
      toast({
        title: 'Eroare la ștergere',
        description: error instanceof Error ? error.message : 'Eroare necunoscută.',
        variant: 'destructive',
        duration: 3000,
      });
    } finally {
      setDeleting(null);
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString('ro-RO');
  };

  const getItemIcon = (item: FileItem) => {
    if (item.type === 'folder') {
      return <Folder className="h-4 w-4 text-blue-500 flex-shrink-0" />;
    }
    if (item.name.toLowerCase().endsWith('.zip')) {
      return <FileArchive className="h-4 w-4 text-orange-500 flex-shrink-0" />;
    }
    return <File className="h-4 w-4 text-primary flex-shrink-0" />;
  };

  const getItemDescription = (item: FileItem) => {
    if (item.type === 'folder') {
      const niftiText = item.nifti_count === 1 ? '1 fișier NIfTI' : `${item.nifti_count} fișiere NIfTI`;
      const totalText = item.files_count === 1 ? '1 fișier total' : `${item.files_count} fișiere total`;

      let description = `${niftiText}, ${totalText}`;

      if (item.segmentation_ready !== undefined) {
        if (item.segmentation_ready) {
          description += ` • Gata pentru segmentare (${item.found_modalities?.join(', ')})`;
        } else if (item.missing_modalities && item.missing_modalities.length > 0) {
          description += ` • Lipsă: ${item.missing_modalities.join(', ')}`;
        }
      }

      return description;
    }
    return item.extension || 'Fișier';
  };

  const getSegmentationStatus = (item: FileItem) => {
    if (item.type !== 'folder' || item.segmentation_ready === undefined) {
      return null;
    }

    if (item.segmentation_ready) {
      return (
        <span className="flex items-center gap-1 text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
          <CheckCircle className="h-3 w-3" />
          Ready pentru AI
        </span>
      );
    } else {
      return (
        <span className="flex items-center gap-1 text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
          <AlertTriangle className="h-3 w-3" />
          Modalități incomplete
        </span>
      );
    }
  };

  useEffect(() => {
    loadFiles();
  }, []);

  return (
    <div className="w-full">
      <div className="flex items-center justify-between mb-6">
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

      {loading ? (
        <div className="text-center py-8">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">Se încarcă elementele...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-8">
          <File className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <p className="text-lg font-medium">Niciun element găsit</p>
          <p className="text-muted-foreground">Nu există fișiere sau foldere pe server.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="text-sm text-muted-foreground mb-4">
            {items.length} element{items.length !== 1 ? 'e' : ''} găsit{items.length !== 1 ? 'e' : ''}
          </div>
          {items.map((item) => (
            <div
              key={item.name}
              className="flex items-center justify-between p-4 border rounded-lg hover:bg-accent/50 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  {getItemIcon(item)}
                  <span className="font-medium truncate">{item.name}</span>
                  {item.type === 'folder' && (
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">
                      Folder
                    </span>
                  )}
                  {getSegmentationStatus(item)}
                </div>
                <div className="flex items-center gap-4 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <HardDrive className="h-3 w-3" />
                    {item.size_mb}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {formatDate(item.modified)}
                  </span>
                  <span>{getItemDescription(item)}</span>
                </div>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDownload(item.name)}
                  disabled={downloading === item.name || deleting === item.name}
                  className="flex items-center gap-1"
                >
                  <Download className="h-3 w-3" />
                  {downloading === item.name ? 'Se descarcă...' : 'Descarcă'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDelete(item.name)}
                  disabled={downloading === item.name || deleting === item.name}
                  className="flex items-center gap-1 text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-3 w-3" />
                  {deleting === item.name ? 'Se șterge...' : 'Șterge'}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}