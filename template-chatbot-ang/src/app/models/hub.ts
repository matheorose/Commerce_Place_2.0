export interface HubClimate {
  low: number;
  high: number;
}

export interface HubLight {
  name: string;
  status: boolean;
}

export interface HubLock {
  name: string;
  isLocked: boolean;
}

export interface Hub {
  climate: HubClimate;
  lights: HubLight[];
  locks: HubLock[];
}
