import { useEffect, useRef } from 'react';
import { useAnalysisStore } from '@/utils/stores/analysis-store';
import { useViewStore } from '@/utils/stores/view-store';
import { useResultsViewerStore } from '@/utils/stores/results-viewer-store';
import { useLocation } from 'react-router-dom';

const CINE_MODE_INTERVAL = 100; // ms

export function useCineMode() {
  const { isCineMode } = useAnalysisStore();
  const location = useLocation();
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Determine which store to use based on current route
  const isResultsPage = location.pathname.includes('/result');

  // Get the appropriate stores
  const analysisViewStore = useViewStore();
  const resultsViewStore = useResultsViewerStore();

  // Use the right store based on current page
  const currentStore = isResultsPage ? resultsViewStore : analysisViewStore;
  const { maxSlices, axis, setSlice } = currentStore;

  useEffect(() => {
    // Start/stop the animation based on cine mode
    if (isCineMode && maxSlices[axis] > 0) {
      console.log(`[CINE] Starting cine mode on ${isResultsPage ? 'results' : 'analysis'} page - axis: ${axis}, maxSlices: ${maxSlices[axis]}`);

      intervalRef.current = setInterval(() => {
        setSlice((currentSlice) => {
          const nextSlice = (currentSlice + 1) % maxSlices[axis];
          return nextSlice;
        });
      }, CINE_MODE_INTERVAL);
    } else {
      if (intervalRef.current) {
        console.log(`[CINE] Stopping cine mode on ${isResultsPage ? 'results' : 'analysis'} page`);
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isCineMode, maxSlices, axis, setSlice, isResultsPage]);

  useEffect(() => {
    // Reset slice to 0 when cine mode is turned on
    const unsub = useAnalysisStore.subscribe((state, prevState) => {
      if (state.isCineMode && !prevState.isCineMode) {
        console.log(`[CINE] Resetting slice to 0 on ${isResultsPage ? 'results' : 'analysis'} page`);
        setSlice(0);
      }
    });

    return unsub;
  }, [setSlice, isResultsPage]);
}