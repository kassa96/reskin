import { Component, input, output, signal } from '@angular/core';

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_SIZE_MB = 10;

@Component({
  selector: 'app-image-dropzone',
  imports: [],
  templateUrl: './image-dropzone.html',
})
export class ImageDropzone {
  readonly previewUrl = input<string | null>(null);

  readonly fileSelected = output<File>();
  readonly validationError = output<string>();

  protected readonly isDragOver = signal(false);

  protected onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver.set(false);
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      this.handleFile(file);
    }
  }

  protected onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragOver.set(true);
  }

  protected onDragLeave(): void {
    this.isDragOver.set(false);
  }

  protected onFileInputChange(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      this.handleFile(file);
    }
    input.value = '';
  }

  private handleFile(file: File): void {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      this.validationError.emit('Format non supporté. Utilisez JPG, PNG ou WEBP.');
      return;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      this.validationError.emit(`L'image dépasse la taille maximale autorisée (${MAX_SIZE_MB} Mo).`);
      return;
    }
    this.fileSelected.emit(file);
  }
}
