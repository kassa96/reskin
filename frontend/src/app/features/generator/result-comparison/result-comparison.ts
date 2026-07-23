import { HttpClient } from '@angular/common/http';
import { Component, inject, input, signal } from '@angular/core';

@Component({
  selector: 'app-result-comparison',
  imports: [],
  templateUrl: './result-comparison.html',
})
export class ResultComparison {
  readonly beforeUrl = input<string | null>(null);
  readonly afterUrl = input<string | null>(null);

  private readonly http = inject(HttpClient);
  protected readonly downloading = signal(false);

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
        link.download = 'produit-personnalise.png';
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
