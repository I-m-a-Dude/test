
import { Bar, BarChart, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { useAnalysisStore } from '@/utils/stores/analysis-store';

export function HistogramChart() {
  const histogramData = useAnalysisStore((state) => state.histogramData);

  return (
    <ChartContainer config={{
        count: {
            label: "Count",
            color: "hsl(var(--chart-1))",
        }
    }} className="w-full h-full">
      <BarChart 
        accessibilityLayer 
        data={histogramData}
        margin={{
            top: 10,
            right: 10,
            left: -20,
            bottom: 0,
        }}
      >
        <XAxis dataKey="value" tickLine={false} axisLine={false} stroke="#888888" fontSize={12} unit="%" />
        <YAxis tickLine={false} axisLine={false} stroke="#888888" fontSize={12} />
        <ChartTooltip
          cursor={false}
          content={<ChartTooltipContent indicator="line" />}
        />
        <Bar dataKey="count" fill="var(--color-count)" radius={4} />
      </BarChart>
    </ChartContainer>
  );
}
