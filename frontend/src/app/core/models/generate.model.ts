export interface GenerateResponse {
  image_url: string;
  description: string;
  request_id: string;
}

export interface Mannequin {
  id: string;
  label: string;
  image_url: string;
}

export interface ApiErrorResponse {
  error: string;
  message: string;
}

export type AppearanceSource = 'reference' | 'original';

export interface ExempleTransformation {
  id: string;
  titre: string;
  categorie: string;
  description: string;
  lien_alibaba: string;
  produit_url: string | null;
  produit_original_url: string | null;
  reference_url: string | null;
  reference_original_url: string | null;
  resultat_url: string;
  resultat_original_url: string;
}
