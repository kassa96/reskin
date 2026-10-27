import { Component, model } from '@angular/core';

interface AspectRatioOption {
  value: string;
  label: string;
}

@Component({
  selector: 'app-aspect-ratio-select',
  templateUrl: './aspect-ratio-select.html',
})
export class AspectRatioSelect {
  readonly value = model('auto');

  protected readonly options: AspectRatioOption[] = [
    { value: 'auto', label: 'Auto' },
    { value: '1:1', label: 'Carré' },
    { value: '4:5', label: 'Portrait' },
    { value: '9:16', label: 'Story' },
    { value: '16:9', label: 'Paysage' },
  ];
}
