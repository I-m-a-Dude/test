import { Bar, BarChart, XAxis, YAxis, ReferenceLine } from 'recharts';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { useAnalysisStore } from '@/utils/stores/analysis-store';

export function HistogramChart() {
  const histogramData = useAnalysisStore((state) => state.histogramData);
  const { windowCenter, windowWidth } = useAnalysisStore();
  
  const minWindow = windowCenter - windowWidth / 2;
  const maxWindow = windowCenter + windowWidth / 2;

  return (
    <ChartContainer config={{
        count: {
            label: "Pixel Count",
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
        <XAxis 
          dataKey="value" 
          tickLine={false} 
          axisLine={false} 
          stroke="#888888" 
          fontSize={10}
          tickFormatter={(value) => `${value}`}
        />
        <YAxis 
          tickLine={false} 
          axisLine={false} 
          stroke="#888888" 
          fontSize={10} 
          tickFormatter={(value) => {
            if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
            if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
            return value.toString();
          }}
        />
        <ChartTooltip
          cursor={false}
          content={<ChartTooltipContent 
            labelFormatter={(value) => `Intensity: ${value}`}
            formatter={(value) => [`${value}`, 'Pixels']}
          />}
        />
        {/* Window boundaries */}
        <ReferenceLine 
          x={Math.round(minWindow)} 
          stroke="hsl(var(--destructive))" 
          strokeDasharray="3 3" 
          strokeWidth={1}
        />
        <ReferenceLine 
          x={Math.round(maxWindow)} 
          stroke="hsl(var(--destructive))" 
          strokeDasharray="3 3" 
          strokeWidth={1}
        />
        <Bar 
          dataKey="count" 
          fill="var(--color-count)" 
          radius={1}
          maxBarSize={5}
        />
      </BarChart>
    </ChartContainer>
  );
}