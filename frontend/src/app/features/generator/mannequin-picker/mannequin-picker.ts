import { Component, input, model } from '@angular/core';

import { Mannequin } from '../../../core/models/generate.model';

@Component({
  selector: 'app-mannequin-picker',
  imports: [],
  templateUrl: './mannequin-picker.html',
})
export class MannequinPicker {
  readonly mannequins = input<Mannequin[]>([]);
  readonly selectedId = model<string | null>(null);

  protected toggle(id: string): void {
    this.selectedId.set(this.selectedId() === id ? null : id);
  }
}
