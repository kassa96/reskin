import { Component, input, output } from '@angular/core';

@Component({
  selector: 'app-error-toast',
  imports: [],
  templateUrl: './error-toast.html',
})
export class ErrorToast {
  readonly message = input.required<string>();
  readonly dismissed = output<void>();
}
