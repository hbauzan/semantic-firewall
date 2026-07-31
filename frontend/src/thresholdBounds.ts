/** Youden recommended thresholds (positive mode) — mirrors backend recommended_thresholds.py */

export const POSITIVE_RECOMMENDED = {
  cosine: 0.5315,
  excitation: 150,
  globalNoise: 4.5,
} as const;

export const NEGATIVE_RECOMMENDED = {
  cosine: 0.6197,
  excitation: 170,
  globalNoise: 4.5,
} as const;

/** Slider ranges centered on positive recommended (midpoint = recommended). */
export const THRESHOLD_SLIDERS = {
  cosine: { min: 0.28, max: 0.78, step: 0.01 },
  excitation: { min: 0, max: 250, step: 1 },
  globalNoise: { min: 1.5, max: 15.0, step: 0.1 },
} as const;
