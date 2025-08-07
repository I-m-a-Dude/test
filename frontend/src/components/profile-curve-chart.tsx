'use client';

import { Line, LineChart, XAxis, YAxis } from 'recharts';
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart';
import { useAnalysisStore } from '@/utils/stores/analysis-store';

export function ProfileCurveChart() {
  const profileCurveData = useAnalysisStore((state) => state.profileCurveData);

  return (
    <ChartContainer config={{
        intensity: {
            label: "Intensity",
            color: "hsl(var(--chart-1))",
        }
    }} className="w-full h-full">
      <LineChart
        accessibilityLayer
        data={profileCurveData}
        margin={{
            top: 10,
            right: 10,
            left: -20,
            bottom: 0,
        }}
      >
        <XAxis
          dataKey="position"
          tickLine={false}
          axisLine={false}
          stroke="#888888"
          fontSize={12}
        />
        <YAxis
          tickLine={false}
          axisLine={false}
          stroke="#888888"
          fontSize={12}
        />
        <ChartTooltip
          cursor={false}
          content={<ChartTooltipContent hideLabel />}
        />
        <Line
          dataKey="intensity"
          type="monotone"
          stroke="var(--color-intensity)"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ChartContainer>
  );
}
