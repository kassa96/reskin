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
