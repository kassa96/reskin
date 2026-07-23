import { Component } from '@angular/core';

import { GeneratorPage } from './features/generator/generator-page/generator-page';

@Component({
  selector: 'app-root',
  imports: [GeneratorPage],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  protected title = 'frontend';
}
