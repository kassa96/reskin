import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, input, output, signal } from '@angular/core';

interface ComparisonPanel {
  label: string;
  url: string | null;
}

@Component({
  selector: 'app-result-comparison',
  imports: [],
  templateUrl: './result-comparison.html',
})
export class ResultComparison {
  readonly beforeUrl = input<string | null>(null);
  readonly personUrl = input<string | null>(null);
  readonly afterUrl = input<string | null>(null);

  readonly imageClicked = output<string>();

  private readonly http = inject(HttpClient);
  protected readonly downloading = signal(false);

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
