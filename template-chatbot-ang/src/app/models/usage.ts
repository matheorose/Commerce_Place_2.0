export type UsageType = 'electricity' | 'water' | 'gas';

export interface Usage {
  day: string;
  amount: number;
  clean: number;
}

export type UsageCollection = Record<UsageType, Usage[]>;
