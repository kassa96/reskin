import { Component } from '@angular/core';

import { GeneratorPage } from '../../generator/generator-page/generator-page';
import { LandingPage } from '../../landing/landing-page/landing-page';

@Component({
  selector: 'app-home-page',
  imports: [LandingPage, GeneratorPage],
  templateUrl: './home-page.html',
})
export class HomePage {}
