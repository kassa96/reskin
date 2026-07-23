import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { GenerateResponse } from '../models/generate.model';

@Injectable({ providedIn: 'root' })
export class ImageGenerationService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  generate(image: File, prompt: string): Observable<GenerateResponse> {
    const formData = new FormData();
    formData.append('image', image);
    formData.append('prompt', prompt);
    return this.http.post<GenerateResponse>(`${this.baseUrl}/api/generate`, formData);
  }
}
