import { Usage, UsageCollection } from '../models/usage';

function generateUsages(startDay: number, days: number): UsageCollection {
  const generateUsage = (
    day: number,
    min: number,
    max: number,
    cleanRatio = 0,
  ): Usage => {
    const amount = Number((Math.random() * (max - min) + min).toFixed(1));

    return {
      day: String(day),
      amount,
      clean: Number((amount * cleanRatio).toFixed(1)),
    };
  };

  const generateSequence = (start: number, count: number) =>
    Array.from({ length: count }, (_, index) => {
      const value = start + index;
      return value > 31 ? value - 31 : value;
    });

  const sequence = generateSequence(startDay, days);

  return {
    water: sequence.map((day) => generateUsage(day, 30, 165)),
    gas: sequence.map((day) => generateUsage(day, 1, 6)),
    electricity: sequence.map((day) => generateUsage(day, 20, 55, 0.55)),
  };
}

export const USAGES: UsageCollection = generateUsages(23, 14);
