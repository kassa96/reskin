import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';

import { ImageGenerationService } from '../../../core/services/image-generation.service';
import { AppearanceSource, ApiErrorResponse, Mannequin } from '../../../core/models/generate.model';
import { AppearanceSelect } from '../appearance-select/appearance-select';
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
    ImageDropzone,
    PromptInput,
    ProductInfoForm,
    AppearanceSelect,
    AspectRatioSelect,
    MannequinPicker,
    ResultComparison,
    ImageLightbox,
    ErrorToast,
  ],
  templateUrl: './generator-page.html',
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
  protected readonly appearanceSource = signal<AppearanceSource>('reference');
  protected readonly keepBackground = signal(false);
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

  protected readonly nothingToDo = computed(
    () =>
      !!this.selectedFile() &&
      !!this.personReferenceUrl() &&
      this.appearanceSource() === 'original' &&
      this.prompt().trim().length === 0,
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
        const file = new File([blob], 'retouche.png', { type: blob.type || 'image/png' });
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
        this.errorMessage.set("Impossible de récupérer l'image générée pour la retoucher.");
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
        anchor.download = 'image-retouchee.png';
        anchor.click();
        setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
      },
      error: () => {
        this.errorMessage.set("Impossible de télécharger l'image retouchée.");
      },
    });
  }

  private handleGenerateError(err: HttpErrorResponse): void {
    this.status.set('error');
    const apiError = err.error as ApiErrorResponse | undefined;
    this.errorMessage.set(
      apiError?.message ??
        (err.status === 0
          ? 'Impossible de contacter le serveur. Vérifiez votre connexion.'
          : 'Une erreur est survenue. Réessayez.'),
    );
  }

  protected dismissError(): void {
    this.errorMessage.set(null);
  }
}
