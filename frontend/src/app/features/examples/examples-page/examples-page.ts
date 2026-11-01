import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ImageGenerationService } from '../../../core/services/image-generation.service';
import { ExempleTransformation } from '../../../core/models/generate.model';

@Component({
  selector: 'app-examples-page',
  imports: [RouterLink],
  templateUrl: './examples-page.html',
  styleUrl: './examples-page.css',
})
export class ExamplesPage {
  private readonly service = inject(ImageGenerationService);

  protected readonly exemples = signal<ExempleTransformation[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  constructor() {
    this.service.getExemples().subscribe({
      next: (exemples) => {
        this.exemples.set(exemples);
        this.loading.set(false);
      },
      error: () => {
        this.error.set(
          "Couldn't load the examples. Make sure the backend is running (http://localhost:8000).",
        );
        this.loading.set(false);
      },
    });
  }
}
