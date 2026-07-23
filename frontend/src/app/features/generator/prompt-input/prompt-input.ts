import { Component, model } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-prompt-input',
  imports: [FormsModule],
  templateUrl: './prompt-input.html',
})
export class PromptInput {
  readonly value = model('');
}
