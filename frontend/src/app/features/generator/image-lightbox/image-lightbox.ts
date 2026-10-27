import { Component, HostListener, input, output } from '@angular/core';

@Component({
  selector: 'app-image-lightbox',
  imports: [],
  templateUrl: './image-lightbox.html',
})
export class ImageLightbox {
  readonly url = input.required<string>();
  readonly altText = input('Aperçu agrandi');
  readonly closed = output<void>();

  @HostListener('document:keydown.escape')
  protected onEscape(): void {
    this.closed.emit();
  }

  protected close(): void {
    this.closed.emit();
  }
}
