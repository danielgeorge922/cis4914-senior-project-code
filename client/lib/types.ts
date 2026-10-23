export type Photo = {
  id: string;
  name: string;
  url: string;
  kind: "fruit" | "leaf";
  file: File;
};

export type Prediction = {
  id: string;
  rank: number;
  name: string;
  matchScore: number;
  image: string;
  imageAlt: string;
  description: string;
  metadata: { label: string; value: string }[];
  traits: string[];
};

export type PredictResponse = {
  demo: boolean;
  predictions: Prediction[];
};
