import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';

import { ImageGenerationService } from '../../../core/services/image-generation.service';
import { ApiErrorResponse } from '../../../core/models/generate.model';
import { ImageDropzone } from '../image-dropzone/image-dropzone';
import { PromptInput } from '../prompt-input/prompt-input';
import { ProductInfoForm } from '../product-info-form/product-info-form';
import { ResultComparison } from '../result-comparison/result-comparison';
import { ErrorToast } from '../error-toast/error-toast';

type Status = 'idle' | 'loading' | 'success' | 'error';
type Step = 1 | 2;

@Component({
  selector: 'app-generator-page',
  imports: [ImageDropzone, PromptInput, ProductInfoForm, ResultComparison, ErrorToast],
  templateUrl: './generator-page.html',
})
export class GeneratorPage {
  private readonly imageGenerationService = inject(ImageGenerationService);

  protected readonly currentStep = signal<Step>(1);

  protected readonly productName = signal('');
  protected readonly productDescription = signal('');

  protected readonly selectedFile = signal<File | null>(null);
  protected readonly previewUrl = signal<string | null>(null);
  protected readonly personImageFile = signal<File | null>(null);
  protected readonly personImagePreviewUrl = signal<string | null>(null);
  protected readonly prompt = signal('');

  protected readonly status = signal<Status>('idle');
  protected readonly resultUrl = signal<string | null>(null);
  protected readonly errorMessage = signal<string | null>(null);

  protected readonly canGoToStep2 = computed(
    () => this.productName().trim().length > 0 && this.productDescription().trim().length > 0,
  );

  protected readonly canSubmit = computed(
    () =>
      this.canGoToStep2() &&
      (!!this.selectedFile() || this.prompt().trim().length > 0) &&
      this.status() !== 'loading',
  );

  protected readonly promptLabel = computed(() =>
    this.selectedFile() ? 'Décrivez la transformation souhaitée (optionnel)' : "Décrivez l'image à générer",
  );

  protected readonly promptPlaceholder = computed(() =>
    this.selectedFile()
      ? 'ex: remplace le fond par un décor de marché africain, lumière chaude'
      : 'ex: Sac en cuir marron posé sur une table en bois, lumière naturelle, ambiance boutique haut de gamme',
  );

  protected readonly promptHint = computed(() =>
    this.selectedFile()
      ? 'Le produit (forme, couleurs, logo) est automatiquement préservé.'
      : "Aucune image fournie : une nouvelle photo du produit est générée à partir de sa description.",
  );

  protected goToStep2(): void {
    if (this.canGoToStep2()) {
      this.currentStep.set(2);
    }
  }

  protected goToStep1(): void {
    this.currentStep.set(1);
  }

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

  protected onImageCleared(): void {
    const previous = this.previewUrl();
    if (previous) {
      URL.revokeObjectURL(previous);
    }
    this.selectedFile.set(null);
    this.previewUrl.set(null);
    this.resultUrl.set(null);
    this.errorMessage.set(null);
    this.status.set('idle');
    this.onPersonImageCleared();
  }

  protected onPersonImageSelected(file: File): void {
    const previous = this.personImagePreviewUrl();
    if (previous) {
      URL.revokeObjectURL(previous);
    }
    this.personImageFile.set(file);
    this.personImagePreviewUrl.set(URL.createObjectURL(file));
  }

  protected onPersonImageCleared(): void {
    const previous = this.personImagePreviewUrl();
    if (previous) {
      URL.revokeObjectURL(previous);
    }
    this.personImageFile.set(null);
    this.personImagePreviewUrl.set(null);
  }

  protected onValidationError(message: string): void {
    this.errorMessage.set(message);
  }

  protected onGenerate(): void {
    const file = this.selectedFile();
    const personFile = this.personImageFile();
    const promptValue = this.prompt().trim();
    const productNameValue = this.productName().trim();
    const productDescriptionValue = this.productDescription().trim();
    if (!productNameValue || !productDescriptionValue || (!file && !promptValue)) {
      return;
    }

    this.status.set('loading');
    this.errorMessage.set(null);

    this.imageGenerationService
      .generate(file, promptValue, productNameValue, productDescriptionValue, personFile)
      .subscribe({
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
