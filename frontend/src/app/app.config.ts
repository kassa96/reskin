import { ApplicationConfig, provideBrowserGlobalErrorListeners, provideZoneChangeDetection } from '@angular/core';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter, withInMemoryScrolling } from '@angular/router';

import { ExamplesPage } from './features/examples/examples-page/examples-page';
import { GeneratorPage } from './features/generator/generator-page/generator-page';
import { HomePage } from './features/home/home-page/home-page';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideHttpClient(),
    provideRouter(
      [
        { path: '', component: HomePage },
        { path: 'outil', component: GeneratorPage },
        { path: 'exemples', component: ExamplesPage },
        { path: '**', redirectTo: '' },
      ],
      withInMemoryScrolling({ anchorScrolling: 'enabled', scrollPositionRestoration: 'enabled' }),
    ),
  ]
};
