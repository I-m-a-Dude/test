import { useState, useEffect } from 'react';
import { Download, Trash2, RefreshCw, File, Calendar, HardDrive, Folder, FileArchive, CheckCircle, AlertTriangle, Eye, FolderOpen, Brain, Archive, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useToast } from '@/utils/hooks/use-toast';
import { useMriStore } from '@/utils/stores/mri-store';
import { getUploadedFiles, downloadFileAttachment, deleteUploadedFile, loadFileForViewing, downloadFolderAsZip, getFolderDetailedInfo } from '@/utils/api';
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

interface FolderDetailedInfo {
  folder_name: string;
  folder_path: string;
  total_files: number;
  total_size: number;
  total_size_mb: string;
  nifti_files_count: number;
  estimated_zip_size_mb: string;
  files: Array<{
    name: string;
    relative_path: string;
    size: number;
    size_mb: string;
    modified: number;
    extension: string;
    is_nifti: boolean;
  }>;
}

interface FileManagerProps {
  onFileLoaded?: () => void;
}

export function FileManager({ onFileLoaded }: FileManagerProps) {
  const [items, setItems] = useState<FileItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [downloadingZip, setDownloadingZip] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [loadingInViewer, setLoadingInViewer] = useState<string | null>(null);

  // States for folder selection
  const [showFolderSelection, setShowFolderSelection] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState<FileItem | null>(null);
  const [selectedNiftiFile, setSelectedNiftiFile] = useState<string | null>(null);
  const [isLoadingSelectedFile, setIsLoadingSelectedFile] = useState(false);

  // States for ZIP download preview
  const [showZipPreview, setShowZipPreview] = useState(false);
  const [zipPreviewFolder, setZipPreviewFolder] = useState<string | null>(null);
  const [zipPreviewInfo, setZipPreviewInfo] = useState<FolderDetailedInfo | null>(null);
  const [loadingZipPreview, setLoadingZipPreview] = useState(false);

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
      description: 'MRI sequence - type not automatically detected',
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
          title: 'No items found',
          description: 'There are no files or folders on the server.',
          duration: 3000,
        });
      }
    } catch (error) {
      console.error('Error loading items:', error);
      toast({
        title: 'Error',
        description: 'Could not load items from the server.',
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
        title: 'Download successful',
        description: `${itemName} has been downloaded.`,
        duration: 3000,
      });
    } catch (error) {
      console.error('Error downloading:', error);
      toast({
        title: 'Download error',
        description: error instanceof Error ? error.message : 'Unknown error.',
        variant: 'destructive',
        duration: 3000,
      });
    } finally {
      setDownloading(null);
    }
  };

  const handleDownloadZipPreview = async (folderName: string) => {
    setZipPreviewFolder(folderName);
    setLoadingZipPreview(true);
    setShowZipPreview(true);

    try {
      const info = await getFolderDetailedInfo(folderName);
      setZipPreviewInfo(info);
    } catch (error) {
      console.error('Error loading folder info:', error);
      toast({
        title: 'Error loading folder info',
        description: error instanceof Error ? error.message : 'Unknown error.',
        variant: 'destructive',
        duration: 3000,
      });
      setShowZipPreview(false);
    } finally {
      setLoadingZipPreview(false);
    }
  };

  const handleConfirmDownloadZip = async () => {
    if (!zipPreviewFolder) return;

    setDownloadingZip(zipPreviewFolder);
    try {
      await downloadFolderAsZip(zipPreviewFolder);
      toast({
        title: 'ZIP download successful! 🎉',
        description: `${zipPreviewFolder}.zip has been downloaded.`,
        duration: 3000,
      });
      setShowZipPreview(false);
    } catch (error) {
      console.error('Error downloading ZIP:', error);
      toast({
        title: 'ZIP download error',
        description: error instanceof Error ? error.message : 'Unknown error.',
        variant: 'destructive',
        duration: 3000,
      });
    } finally {
      setDownloadingZip(null);
    }
  };

  const handleLoadInViewer = async (itemName: string) => {
    const item = items.find(i => i.name === itemName);
    if (!item || item.type !== 'file' || !item.name.match(/\.nii(\.gz)?$/)) {
      toast({
        title: 'Invalid file',
        description: 'Only .nii and .nii.gz files can be loaded in the viewer.',
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
        title: 'File loaded in viewer!',
        description: `${itemName} is now available for viewing.`,
        duration: 3000,
      });

      if (onFileLoaded) {
        onFileLoaded();
      }
    } catch (error) {
      console.error('Error loading in viewer:', error);
      toast({
        title: 'Error loading in viewer',
        description: error instanceof Error ? error.message : 'Unknown error.',
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
        title: 'Invalid folder',
        description: 'The folder must contain at least 2 NIfTI files.',
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
        title: 'File successfully selected!',
        description: `${filename} has been loaded and is ready for analysis.`,
      });

      setShowFolderSelection(false);
      setSelectedFolder(null);

      if (onFileLoaded) {
        onFileLoaded();
      }

    } catch (error) {
      console.error('Error loading selected file:', error);
      toast({
        title: 'Error loading file',
        description: error instanceof Error ? error.message : 'Could not load the selected file.',
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
        title: 'Item deleted',
        description: `${itemName} has been deleted from the server.`,
        duration: 3000,
      });
    } catch (error) {
      console.error('Error deleting:', error);
      toast({
        title: 'Delete error',
        description: error instanceof Error ? error.message : 'Unknown error.',
        variant: 'destructive',
        duration: 3000,
      });
    } finally {
      setDeleting(null);
    }
  };

  const formatDate = (timestamp: number) => {
    return new Date(timestamp * 1000).toLocaleString('en-US');
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
      const niftiText = item.nifti_count === 1 ? '1 NIfTI file' : `${item.nifti_count} NIfTI files`;
      const totalText = item.files_count === 1 ? '1 total file' : `${item.files_count} total files`;

      let description = `${niftiText}, ${totalText}`;

      if (item.segmentation_ready !== undefined) {
        if (item.segmentation_ready) {
          description += ` • Ready for segmentation (${item.found_modalities?.join(', ')})`;
        } else if (item.missing_modalities && item.missing_modalities.length > 0) {
          description += ` • Missing: ${item.missing_modalities.join(', ')}`;
        }
      }

      return description;
    }
    return item.extension || 'File';
  };

  const getSegmentationStatus = (item: FileItem) => {
    if (item.type !== 'folder' || item.segmentation_ready === undefined) {
      return null;
    }

    if (item.segmentation_ready) {
      return (
        <span className="flex items-center gap-1 text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
          <CheckCircle className="h-3 w-3" />
          Ready for AI
        </span>
      );
    } else {
      return (
        <span className="flex items-center gap-1 text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
          <AlertTriangle className="h-3 w-3" />
          Incomplete modalities
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

  const canDownloadAsZip = (item: FileItem) => {
    return item.type === 'folder' && item.files_count && item.files_count > 0;
  };

  useEffect(() => {
    loadFiles();
  }, []);

  // ZIP Preview Dialog
  const ZipPreviewDialog = () => (
    <Dialog open={showZipPreview} onOpenChange={setShowZipPreview}>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Archive className="h-5 w-5" />
            Download {zipPreviewFolder} as ZIP
          </DialogTitle>
          <DialogDescription>
            Preview of files that will be included in the ZIP download.
          </DialogDescription>
        </DialogHeader>

        {loadingZipPreview ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin mr-2" />
            Loading folder information...
          </div>
        ) : zipPreviewInfo && (
          <div className="space-y-4">
            {/* Summary */}
            <div className="grid grid-cols-2 gap-4 p-4 bg-muted/30 rounded-lg">
              <div>
                <div className="text-sm text-muted-foreground">Total Files</div>
                <div className="font-semibold">{zipPreviewInfo.total_files}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">NIfTI Files</div>
                <div className="font-semibold">{zipPreviewInfo.nifti_files_count}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Original Size</div>
                <div className="font-semibold">{zipPreviewInfo.total_size_mb}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Est. ZIP Size</div>
                <div className="font-semibold">{zipPreviewInfo.estimated_zip_size_mb}</div>
              </div>
            </div>

            {/* File List */}
            <div className="space-y-2">
              <h4 className="font-medium text-sm">Files to be included:</h4>
              <ScrollArea className="h-48 border rounded-md p-2">
                <div className="space-y-1">
                  {zipPreviewInfo.files.map((file, index) => (
                    <div key={index} className="flex items-center justify-between text-xs p-2 hover:bg-muted/50 rounded">
                      <div className="flex items-center gap-2 min-w-0 flex-1">
                        {file.is_nifti ? (
                          <Brain className="h-3 w-3 text-blue-500 flex-shrink-0" />
                        ) : (
                          <File className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                        )}
                        <span className="truncate">{file.relative_path}</span>
                        {file.is_nifti && (
                          <Badge variant="outline" className="text-xs">NIfTI</Badge>
                        )}
                      </div>
                      <span className="text-muted-foreground ml-2">{file.size_mb}</span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-4">
              <Button
                variant="outline"
                onClick={() => setShowZipPreview(false)}
                disabled={downloadingZip !== null}
              >
                Cancel
              </Button>
              <Button
                onClick={handleConfirmDownloadZip}
                disabled={downloadingZip !== null}
                className="flex items-center gap-2"
              >
                {downloadingZip ? (
                  <>
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    Creating ZIP...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4" />
                    Download ZIP ({zipPreviewInfo.estimated_zip_size_mb})
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );

  // Folder selection modal
  if (showFolderSelection && selectedFolder) {
    return (
      <div className="w-full">
        <Card className="w-full">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="h-6 w-6 text-primary" />
              Select MRI Modality from {selectedFolder.name}
            </CardTitle>
            <CardDescription>
              The folder contains {selectedFolder.nifti_count} NIfTI files.
              Choose the modality you want to view.
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
                          Loading...
                        </div>
                      ) : (
                        <Button variant="outline" size="sm">
                          <Eye className="h-4 w-4 mr-1" />
                          Select
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
                Cancel
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
          Refresh
        </Button>
      </div>

      {loading ? (
        <div className="text-center py-8">
          <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-4 text-muted-foreground" />
          <p className="text-muted-foreground">Loading items...</p>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-8">
          <File className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <p className="text-lg font-medium">No items found</p>
          <p className="text-muted-foreground">There are no files or folders on the server.</p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="text-sm text-muted-foreground mb-4">
            {items.length} item{items.length !== 1 ? 's' : ''} found
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
                {/* Button for folder usage */}
                {canUseFolder(item) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleUseFolderClick(item)}
                    disabled={downloading === item.name || deleting === item.name || loadingInViewer === item.name || downloadingZip === item.name}
                    className="flex items-center gap-1"
                  >
                    <FolderOpen className="h-3 w-3" />
                    Use Folder
                  </Button>
                )}

                {/* Button for loading in viewer - only for NIfTI files */}
                {canLoadInViewer(item) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleLoadInViewer(item.name)}
                    disabled={loadingInViewer === item.name || downloading === item.name || deleting === item.name || downloadingZip === item.name}
                    className="flex items-center gap-1"
                  >
                    <Eye className="h-3 w-3" />
                    {loadingInViewer === item.name ? 'Loading...' : 'View in viewer'}
                  </Button>
                )}

                {/* Download individual files */}
                {item.type === 'file' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownload(item.name)}
                    disabled={downloading === item.name || deleting === item.name || loadingInViewer === item.name || downloadingZip === item.name}
                    className="flex items-center gap-1"
                  >
                    <Download className="h-3 w-3" />
                    {downloading === item.name ? 'Downloading...' : 'Download'}
                  </Button>
                )}

                {/* Download folder as ZIP */}
                {canDownloadAsZip(item) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDownloadZipPreview(item.name)}
                    disabled={downloading === item.name || deleting === item.name || loadingInViewer === item.name || downloadingZip === item.name}
                    className="flex items-center gap-1"
                  >
                    <Archive className="h-3 w-3" />
                    {downloadingZip === item.name ? 'Creating ZIP...' : 'Download ZIP'}
                  </Button>
                )}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDelete(item.name)}
                  disabled={downloading === item.name || deleting === item.name || loadingInViewer === item.name || downloadingZip === item.name}
                  className="flex items-center gap-1 text-destructive hover:text-destructive"
                >
                  <Trash2 className="h-3 w-3" />
                  {deleting === item.name ? 'Deleting...' : 'Delete'}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ZIP Preview Dialog */}
      <ZipPreviewDialog />
    </div>
  );
}