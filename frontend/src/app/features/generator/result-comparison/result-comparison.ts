import { HttpClient } from '@angular/common/http';
import { Component, DestroyRef, computed, effect, inject, input, output, signal } from '@angular/core';

interface ComparisonPanel {
  label: string;
  url: string | null;
}

// Rotating status messages shown while the AI image is being generated.
// Generation can take a minute or two, so the step advances every few seconds
// to reassure the user that work is still in progress.
const LOADING_STEPS = [
  'Analyzing your product…',
  'Building the African setting…',
  'Placing the product in the scene…',
  'Polishing the final image…',
];
const STEP_DURATION_S = 12;

@Component({
  selector: 'app-result-comparison',
  imports: [],
  templateUrl: './result-comparison.html',
})
export class ResultComparison {
  readonly beforeUrl = input<string | null>(null);
  readonly personUrl = input<string | null>(null);
  readonly afterUrl = input<string | null>(null);
  readonly loading = input(false);

  readonly imageClicked = output<string>();

  private readonly http = inject(HttpClient);
  protected readonly downloading = signal(false);
  protected readonly loadingSteps = LOADING_STEPS;
  protected readonly loadingStepIndex = signal(0);
  protected readonly elapsedSeconds = signal(0);

  constructor() {
    const destroyRef = inject(DestroyRef);
    let timer: ReturnType<typeof setInterval> | null = null;
    // allowSignalWrites: the effect resets the step/elapsed counters when a new
    // generation starts; the per-second ticks happen outside the effect.
    effect(
      () => {
        if (this.loading()) {
          this.loadingStepIndex.set(0);
          this.elapsedSeconds.set(0);
          timer = setInterval(() => {
            const next = this.elapsedSeconds() + 1;
            this.elapsedSeconds.set(next);
            this.loadingStepIndex.set(
              Math.min(Math.floor(next / STEP_DURATION_S), LOADING_STEPS.length - 1),
            );
          }, 1000);
        } else if (timer !== null) {
          clearInterval(timer);
          timer = null;
        }
      },
      { allowSignalWrites: true },
    );
    destroyRef.onDestroy(() => {
      if (timer !== null) {
        clearInterval(timer);
      }
    });
  }

  protected readonly panels = computed<ComparisonPanel[]>(() => {
    const panels: ComparisonPanel[] = [{ label: 'Before', url: this.beforeUrl() }];
    if (this.personUrl()) {
      panels.push({ label: 'Person', url: this.personUrl() });
    }
    panels.push({ label: 'After', url: this.afterUrl() });
    return panels;
  });

  protected download(): void {
    const url = this.afterUrl();
    if (!url) {
      return;
    }
    this.downloading.set(true);
    this.http.get(url, { responseType: 'blob' }).subscribe({
      next: (blob) => {
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = objectUrl;
        link.download = 'customized-product.png';
        link.click();
        URL.revokeObjectURL(objectUrl);
        this.downloading.set(false);
      },
      error: () => {
        this.downloading.set(false);
        window.open(url, '_blank');
      },
    });
  }
}
