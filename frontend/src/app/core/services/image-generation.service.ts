import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AppearanceSource, GenerateResponse, Mannequin } from '../models/generate.model';

@Injectable({ providedIn: 'root' })
export class ImageGenerationService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  generate(
    image: File | null,
    prompt: string,
    productName: string,
    productDescription: string,
    personImage: File | null = null,
    aspectRatio = 'auto',
    mannequinId: string | null = null,
    keepBackground = false,
    appearanceSource: AppearanceSource = 'reference',
  ): Observable<GenerateResponse> {
    const formData = new FormData();
    if (image) {
      formData.append('image', image);
    }
    if (personImage) {
      formData.append('person_image', personImage);
    }
    if (mannequinId) {
      formData.append('mannequin_id', mannequinId);
    }
    formData.append('prompt', prompt);
    formData.append('product_name', productName);
    formData.append('product_description', productDescription);
    formData.append('aspect_ratio', aspectRatio);
    formData.append('keep_background', String(keepBackground));
    formData.append('appearance_source', appearanceSource);
    return this.http.post<GenerateResponse>(`${this.baseUrl}/api/generate`, formData);
  }

  getMannequins(): Observable<Mannequin[]> {
    return this.http
      .get<Mannequin[]>(`${this.baseUrl}/api/mannequins`)
      .pipe(
        map((mannequins) =>
          mannequins.map((m) => ({ ...m, image_url: `${this.baseUrl}${m.image_url}` })),
        ),
      );
  }
}
