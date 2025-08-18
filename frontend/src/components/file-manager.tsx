import { useState, useEffect } from 'react';
import { Download, Trash2, RefreshCw, File, Calendar, HardDrive, Folder, FileArchive, CheckCircle, AlertTriangle, Eye, FolderOpen, Brain } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/utils/hooks/use-toast';
import { useMriStore } from '@/utils/stores/mri-store';
import { getUploadedFiles, downloadFileAttachment, deleteUploadedFile, loadFileForViewing } from '@/utils/api';
import { cn } from '@/utils/cn';

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

interface FileManagerProps {
  onFileLoaded?: () => void;
}

export function FileManager({ onFileLoaded }: FileManagerProps) {
  const [items, setItems] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [loadingInViewer, setLoadingInViewer] = useState<string | null>(null);

  // States pentru folder selection
  const [showFolderSelection, setShowFolderSelection] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState<FileItem | null>(null);
  const [selectedNiftiFile, setSelectedNiftiFile] = useState<string | null>(null);
  const [isLoadingSelectedFile, setIsLoadingSelectedFile] = useState(false);

  const { toast } = useToast();
  const { setFile, setLastKnownBackendFile } = useMriStore();

  const getMriModalityInfo = (filename: string) => {
    const lower = filename.toLowerCase();

    if (lower.includes('t1') && (lower.includes('gd') || lower.includes('c') || lower.includes('contrast'))) {
      return {
        type: 'T1C',
        label: 'T1 with Contrast',
        color: 'bg-red-100 text-red-800 border-red-200'
      };
    } else if (lower.includes('t1')) {
      return {
        type: 'T1N',
        label: 'T1 Native',
        color: 'bg-blue-100 text-blue-800 border-blue-200'
      };
    } else if (lower.includes('t2') && lower.includes('flair') || lower.includes('f')) {
      return {
        type: 'T2F',
        label: 'T2 FLAIR',
        color: 'bg-purple-100 text-purple-800 border-purple-200'
      };
    } else if (lower.includes('t2')) {
      return {
        type: 'T2W',
        label: 'T2 Weighted',
        color: 'bg-green-100 text-green-800 border-green-200'
      };
    }

    return {
      type: 'OTHER',
      label: 'Other MRI',
      description: 'Secvență MRI - tip nedetectat automat',
      color: 'bg-gray-100 text-gray-800 border-gray-200',
      icon: '⚪'
    };
  };

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

  const handleLoadInViewer = async (itemName: string) => {
    const item = items.find(i => i.name === itemName);
    if (!item || item.type !== 'file' || !item.name.match(/\.nii(\.gz)?$/)) {
      toast({
        title: 'Fișier invalid',
        description: 'Doar fișierele .nii și .nii.gz pot fi încărcate în viewer.',
        variant: 'destructive',
        duration: 3000,
      });
      return;
    }

    setLoadingInViewer(itemName);
    try {
      const file = await loadFileForViewing(itemName);
      setFile(file);
      setLastKnownBackendFile(itemName);

      toast({
        title: 'Fișier încărcat în viewer!',
        description: `${itemName} este acum disponibil pentru vizualizare.`,
        duration: 3000,
      });

      if (onFileLoaded) {
        onFileLoaded();
      }
    } catch (error) {
      console.error('Eroare la încărcarea în viewer:', error);
      toast({
        title: 'Eroare la încărcarea în viewer',
        description: error instanceof Error ? error.message : 'Eroare necunoscută.',
        variant: 'destructive',
        duration: 3000,
      });
    } finally {
      setLoadingInViewer(null);
    }
  };

  const handleUseFolderClick = (folder: FileItem) => {
    if (folder.type !== 'folder' || !folder.nifti_files || folder.nifti_files.length <= 1) {
      toast({
        title: 'Folder invalid',
        description: 'Folderul trebuie să conțină cel puțin 2 fișiere NIfTI.',
        variant: 'destructive',
        duration: 3000,
      });
      return;
    }

    setSelectedFolder(folder);
    setShowFolderSelection(true);
  };

  const handleNiftiFileSelection = async (filename: string) => {
    setIsLoadingSelectedFile(true);
    setSelectedNiftiFile(filename);

    try {
      const loadedFile = await loadFileForViewing(filename);

      setFile(loadedFile);
      setLastKnownBackendFile(filename);

      toast({
        title: 'Fișier selectat cu succes!',
        description: `${filename} a fost încărcat și este gata pentru analiză.`,
      });

      // Închide selecția și notifică părinte
      setShowFolderSelection(false);
      setSelectedFolder(null);

      if (onFileLoaded) {
        onFileLoaded();
      }

    } catch (error) {
      console.error('Error loading selected file:', error);
      toast({
        title: 'Eroare la încărcarea fișierului',
        description: error instanceof Error ? error.message : 'Nu s-a putut încărca fișierul selectat.',
        variant: 'destructive',
      });
    } finally {
      setIsLoadingSelectedFile(false);
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

  const canLoadInViewer = (item: FileItem) => {
    return item.type === 'file' && item.name.match(/\.nii(\.gz)?$/);
  };

  const canUseFolder = (item: FileItem) => {
    return item.type === 'folder' && item.nifti_count && item.nifti_count > 1;
  };

  useEffect(() => {
    loadFiles();
  }, []);

  // Folder selection modal
  if (showFolderSelection && selectedFolder) {
    return (
      <div className="w-full">
        <Card className="w-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-6 w-6 text-primary" />
              Selectează Modalitatea MRI din {selectedFolder.name}
            </CardTitle>
            <CardDescription>
              Folderul conține {selectedFolder.nifti_count} fișiere NIfTI.
              Alege modalitatea pe care dorești să o vizualizezi.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {selectedFolder.nifti_files?.map((filename) => {
                const modalityInfo = getMriModalityInfo(filename);
                const isSelected = selectedNiftiFile === filename;
                const isLoading = isLoadingSelectedFile && isSelected;

                return (
                  <div
                    key={filename}
                    className={cn(
                      "flex items-center justify-between p-4 border rounded-lg transition-all cursor-pointer hover:bg-accent/50",
                      isSelected && "ring-2 ring-primary bg-accent/30"
                    )}
                    onClick={() => !isLoading && handleNiftiFileSelection(filename)}
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div className="text-2xl">{modalityInfo.icon}</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="font-medium truncate">{filename}</h4>
                          <Badge
                            variant="outline"
                            className={cn("text-xs", modalityInfo.color)}
                          >
                            {modalityInfo.type}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {modalityInfo.description}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {isLoading ? (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <RefreshCw className="h-4 w-4 animate-spin" />
                          Se încarcă...
                        </div>
                      ) : (
                        <Button variant="outline" size="sm">
                          <Eye className="h-4 w-4 mr-1" />
                          Selectează
                        </Button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-6 flex justify-center">
              <Button
                variant="outline"
                onClick={() => {
                  setShowFolderSelection(false);
                  setSelectedFolder(null);
                }}
                disabled={isLoadingSelectedFile}
              >
                Anulează
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Main file manager view
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
                {/* Buton pentru folder usage */}
                {canUseFolder(item) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleUseFolderClick(item)}
                    disabled={downloading === item.name || deleting === item.name || loadingInViewer === item.name}
                    className="flex items-center gap-1"
                  >
                    <FolderOpen className="h-3 w-3" />
                    Folosește Folder
                  </Button>
                )}

                {/* Buton pentru încărcarea în viewer - doar pentru fișiere NIfTI */}
                {canLoadInViewer(item) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleLoadInViewer(item.name)}
                    disabled={loadingInViewer === item.name || downloading === item.name || deleting === item.name}
                    className="flex items-center gap-1"
                  >
                    <Eye className="h-3 w-3" />
                    {loadingInViewer === item.name ? 'Se încarcă...' : 'Vezi în viewer'}
                  </Button>
                )}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDownload(item.name)}
                  disabled={downloading === item.name || deleting === item.name || loadingInViewer === item.name}
                  className="flex items-center gap-1"
                >
                  <Download className="h-3 w-3" />
                  {downloading === item.name ? 'Se descarcă...' : 'Descarcă'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDelete(item.name)}
                  disabled={downloading === item.name || deleting === item.name || loadingInViewer === item.name}
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