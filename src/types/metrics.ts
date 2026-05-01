// Types for exporter metrics
export type Point = { x: number; y: number };

export interface MetricsState {
  cpu: { t: number; v: number }[];
  memory: { t: number; v: number }[];
  disk: { t: number; v: number }[];
  network: { t: number; v: number }[];
  extras?: { name: string; data: { t: number; v: number }[] }[];
}
