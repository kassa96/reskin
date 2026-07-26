import { Component, model } from '@angular/core';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-product-info-form',
  imports: [FormsModule],
  templateUrl: './product-info-form.html',
})
export class ProductInfoForm {
  readonly name = model('');
  readonly description = model('');
}
