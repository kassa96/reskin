import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';

import { ImageGenerationService } from '../../../core/services/image-generation.service';
import { ApiErrorResponse } from '../../../core/models/generate.model';
import { ImageDropzone } from '../image-dropzone/image-dropzone';
import { PromptInput } from '../prompt-input/prompt-input';
import { ResultComparison } from '../result-comparison/result-comparison';
import { ErrorToast } from '../error-toast/error-toast';

type Status = 'idle' | 'loading' | 'success' | 'error';

@Component({
  selector: 'app-generator-page',
  imports: [ImageDropzone, PromptInput, ResultComparison, ErrorToast],
  templateUrl: './generator-page.html',
})
export class GeneratorPage {
  private readonly imageGenerationService = inject(ImageGenerationService);

  protected readonly selectedFile = signal<File | null>(null);
  protected readonly previewUrl = signal<string | null>(null);
  protected readonly prompt = signal('');
  protected readonly status = signal<Status>('idle');
  protected readonly resultUrl = signal<string | null>(null);
  protected readonly errorMessage = signal<string | null>(null);

  protected readonly canSubmit = computed(
    () => !!this.selectedFile() && this.prompt().trim().length > 0 && this.status() !== 'loading',
  );

  protected onFileSelected(file: File): void {
    const previous = this.previewUrl();
    if (previous) {
      URL.revokeObjectURL(previous);
    }
    this.selectedFile.set(file);
    this.previewUrl.set(URL.createObjectURL(file));
    this.resultUrl.set(null);
    this.errorMessage.set(null);
    this.status.set('idle');
  }

  protected onValidationError(message: string): void {
    this.errorMessage.set(message);
  }

  protected onGenerate(): void {
    const file = this.selectedFile();
    const promptValue = this.prompt().trim();
    if (!file || !promptValue) {
      return;
    }

    this.status.set('loading');
    this.errorMessage.set(null);

    this.imageGenerationService.generate(file, promptValue).subscribe({
      next: (response) => {
        this.resultUrl.set(response.image_url);
        this.status.set('success');
      },
      error: (err: HttpErrorResponse) => {
        this.status.set('error');
        const apiError = err.error as ApiErrorResponse | undefined;
        this.errorMessage.set(
          apiError?.message ??
            (err.status === 0
              ? 'Impossible de contacter le serveur. Vérifiez votre connexion.'
              : 'Une erreur est survenue. Réessayez.'),
        );
      },
    });
  }

  protected dismissError(): void {
    this.errorMessage.set(null);
  }
}
