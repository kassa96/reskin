import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { GenerateResponse } from '../models/generate.model';

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
  ): Observable<GenerateResponse> {
    const formData = new FormData();
    if (image) {
      formData.append('image', image);
    }
    if (personImage) {
      formData.append('person_image', personImage);
    }
    formData.append('prompt', prompt);
    formData.append('product_name', productName);
    formData.append('product_description', productDescription);
    return this.http.post<GenerateResponse>(`${this.baseUrl}/api/generate`, formData);
  }
}
