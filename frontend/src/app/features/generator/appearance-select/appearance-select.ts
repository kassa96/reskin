import { Component, model } from '@angular/core';

import { AppearanceSource } from '../../../core/models/generate.model';

interface AppearanceOption {
  value: AppearanceSource;
  label: string;
}

@Component({
  selector: 'app-appearance-select',
  templateUrl: './appearance-select.html',
})
export class AppearanceSelect {
  readonly value = model<AppearanceSource>('reference');

  protected readonly options: AppearanceOption[] = [
    { value: 'reference', label: 'Nouvelle personne' },
    { value: 'original', label: "Personne d'origine" },
  ];
}
