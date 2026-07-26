import { Component, input, model } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-prompt-input',
  imports: [FormsModule],
  templateUrl: './prompt-input.html',
})
export class PromptInput {
  readonly value = model('');
  readonly label = input('Décrivez la transformation souhaitée');
  readonly placeholder = input(
    'ex: remplace le fond par un décor de marché africain, lumière chaude',
  );
  readonly hint = input('Le produit (forme, couleurs, logo) est automatiquement préservé.');
}
