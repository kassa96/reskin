import { Component, input, model } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-prompt-input',
  imports: [FormsModule],
  templateUrl: './prompt-input.html',
})
export class PromptInput {
  readonly value = model('');
  readonly label = input('Describe the transformation you want');
  readonly placeholder = input(
    'e.g. replace the background with an African market setting, warm light',
  );
  readonly hint = input('The product (shape, colours, logo) is automatically preserved.');
}
