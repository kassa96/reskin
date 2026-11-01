import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ImageGenerationService } from '../../../core/services/image-generation.service';
import { AppearanceSource, ApiErrorResponse, Mannequin } from '../../../core/models/generate.model';
import { AspectRatioSelect } from '../aspect-ratio-select/aspect-ratio-select';
import { ImageDropzone } from '../image-dropzone/image-dropzone';
import { ImageLightbox } from '../image-lightbox/image-lightbox';
import { MannequinPicker } from '../mannequin-picker/mannequin-picker';
import { PromptInput } from '../prompt-input/prompt-input';
import { ProductInfoForm } from '../product-info-form/product-info-form';
import { ResultComparison } from '../result-comparison/result-comparison';
import { ErrorToast } from '../error-toast/error-toast';

type Status = 'idle' | 'loading' | 'success' | 'error';
type Step = 1 | 2;

@Component({
  selector: 'app-generator-page',
  imports: [
    RouterLink,
    ImageDropzone,
    PromptInput,
    ProductInfoForm,
    AspectRatioSelect,
    MannequinPicker,
    ResultComparison,
    ImageLightbox,
    ErrorToast,
  ],
  templateUrl: './generator-page.html',
  styleUrl: './generator-page.css',
})
export class GeneratorPage {
  private readonly imageGenerationService = inject(ImageGenerationService);
  private readonly http = inject(HttpClient);

  constructor() {
    this.imageGenerationService.getMannequins().subscribe({
      next: (mannequins) => this.mannequins.set(mannequins),
      error: () => {
        // Optional default gallery — failing to load it doesn't block the
        // custom-upload flow, so no user-facing error here.
      },
    });
  }

  protected readonly currentStep = signal<Step>(1);

  protected readonly productName = signal('');
  protected readonly productDescription = signal('');

  protected readonly selectedFile = signal<File | null>(null);
  protected readonly previewUrl = signal<string | null>(null);
  protected readonly personImageFile = signal<File | null>(null);
  protected readonly personImagePreviewUrl = signal<string | null>(null);
  protected readonly mannequins = signal<Mannequin[]>([]);
  protected readonly selectedMannequinId = signal<string | null>(null);
  protected readonly prompt = signal('');
  protected readonly aspectRatio = signal('auto');
  // Pinned value: "New person" (the appearance field was removed from the form).
  protected readonly appearanceSource = signal<AppearanceSource>('reference');
  protected readonly keepBackground = signal(true);
  protected readonly refinePrompt = signal('');

  protected readonly status = signal<Status>('idle');
  protected readonly resultUrl = signal<string | null>(null);
  protected readonly refinedUrl = signal<string | null>(null);
  protected readonly errorMessage = signal<string | null>(null);
  protected readonly lightboxUrl = signal<string | null>(null);

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
    this.selectedFile() ? 'Describe the transformation you want (optional)' : 'Describe the image to generate',
  );

  protected readonly promptPlaceholder = computed(() =>
    this.selectedFile()
      ? 'e.g. replace the background with an African market scene, warm light'
      : 'e.g. Brown leather bag on a wooden table, natural light, upscale boutique mood',
  );

  protected readonly promptHint = computed(() =>
    this.selectedFile()
      ? 'The product (shape, colours, logo) is automatically preserved.'
      : 'No image provided: a new photo of the product is generated from its description.',
  );

  protected readonly canRefine = computed(
    () =>
      (!!this.resultUrl() || !!this.refinedUrl()) &&
      this.refinePrompt().trim().length > 0 &&
      this.status() !== 'loading',
  );

  protected readonly personReferenceUrl = computed(
    () =>
      this.personImagePreviewUrl() ??
      this.mannequins().find((m) => m.id === this.selectedMannequinId())?.image_url ??
      null,
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
    this.refinedUrl.set(null);
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
    this.refinedUrl.set(null);
    this.errorMessage.set(null);
    this.status.set('idle');
    this.onPersonImageCleared();
    this.selectedMannequinId.set(null);
  }

  protected onPersonImageSelected(file: File): void {
    const previous = this.personImagePreviewUrl();
    if (previous) {
      URL.revokeObjectURL(previous);
    }
    this.personImageFile.set(file);
    this.personImagePreviewUrl.set(URL.createObjectURL(file));
    this.selectedMannequinId.set(null);
  }

  protected onPersonImageCleared(): void {
    const previous = this.personImagePreviewUrl();
    if (previous) {
      URL.revokeObjectURL(previous);
    }
    this.personImageFile.set(null);
    this.personImagePreviewUrl.set(null);
  }

  protected onMannequinSelected(mannequinId: string | null): void {
    if (mannequinId) {
      this.onPersonImageCleared();
    }
    this.selectedMannequinId.set(mannequinId);
  }

  protected onValidationError(message: string): void {
    this.errorMessage.set(message);
  }

  protected onKeepBackgroundChange(event: Event): void {
    const input = event.target as HTMLInputElement | null;
    this.keepBackground.set(input?.checked ?? false);
  }

  protected openLightbox(url: string): void {
    this.lightboxUrl.set(url);
  }

  protected closeLightbox(): void {
    this.lightboxUrl.set(null);
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
      .generate(
        file,
        promptValue,
        productNameValue,
        productDescriptionValue,
        personFile,
        this.aspectRatio(),
        this.selectedMannequinId(),
        this.keepBackground(),
        this.appearanceSource(),
      )
      .subscribe({
        next: (response) => {
          this.resultUrl.set(response.image_url);
          this.refinedUrl.set(null);
          this.status.set('success');
        },
        error: (err: HttpErrorResponse) => this.handleGenerateError(err),
      });
  }

  protected onRefine(): void {
    const currentResult = this.refinedUrl() ?? this.resultUrl();
    const refineValue = this.refinePrompt().trim();
    if (!currentResult || !refineValue) {
      return;
    }

    this.status.set('loading');
    this.errorMessage.set(null);

    this.http.get(currentResult, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        const file = new File([blob], 'retouch.png', { type: blob.type || 'image/png' });
        this.imageGenerationService
          .generate(
            file,
            refineValue,
            this.productName().trim(),
            this.productDescription().trim(),
            null,
            this.aspectRatio(),
            null,
            this.keepBackground(),
            this.appearanceSource(),
          )
          .subscribe({
            next: (response) => {
              this.refinedUrl.set(response.image_url);
              this.refinePrompt.set('');
              this.status.set('success');
            },
            error: (err: HttpErrorResponse) => this.handleGenerateError(err),
          });
      },
      error: () => {
        this.status.set('error');
        this.errorMessage.set("Couldn't fetch the generated image for retouching.");
      },
    });
  }

  protected onDownloadRefined(): void {
    const url = this.refinedUrl();
    if (!url) {
      return;
    }
    this.http.get(url, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        const objectUrl = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = objectUrl;
        anchor.download = 'retouched-image.png';
        anchor.click();
        setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      },
      error: () => {
        this.errorMessage.set("Couldn't download the retouched image.");
      },
    });
  }

  private handleGenerateError(err: HttpErrorResponse): void {
    this.status.set('error');
    const apiError = err.error as ApiErrorResponse | undefined;
    this.errorMessage.set(
      apiError?.message ??
        (err.status === 0
          ? "Can't reach the server. Check your connection."
          : 'Something went wrong. Please try again.'),
    );
  }

  protected dismissError(): void {
    this.errorMessage.set(null);
  }
}
