
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useAnalysisStore } from '@/utils/stores/analysis-store';
import { BrainCircuit } from 'lucide-react';

export function MetadataViewerDialog() {
  const {
    showMetadataViewer,
    setShowMetadataViewer,
    metadata,
  } = useAnalysisStore();

  const handleOpenChange = (open: boolean) => {
    setShowMetadataViewer(open);
  };

  return (
    <Dialog open={showMetadataViewer} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BrainCircuit className="w-6 h-6" />
            NIfTI Metadata
          </DialogTitle>
          <DialogDescription>
            Detailed information from the NIfTI file header.
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="h-96 w-full">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-[200px]">Field</TableHead>
                <TableHead>Value</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {metadata && Object.entries(metadata).map(([key, value]) => (
                <TableRow key={key}>
                  <TableCell className="font-medium break-all">{key}</TableCell>
                  <TableCell className="font-mono text-xs break-all">
                    {Array.isArray(value) ? value.join(', ') : String(value)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
}
