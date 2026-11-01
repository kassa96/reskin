import { Component, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

interface Demo {
  id: string;
  tab: string;
  produit: string;
  categorie: string;
  avant: string;
  reference: string;
  apres: string;
  transformation: string;
  lienAlibaba: string;
}

@Component({
  selector: 'app-landing-page',
  imports: [RouterLink],
  templateUrl: './landing-page.html',
  styleUrl: './landing-page.css',
})
export class LandingPage {
  protected readonly demos: Demo[] = [
    {
      id: 'pyjama',
      tab: 'Pyjamas',
      produit: 'Pink fleece pyjamas',
      categorie: 'Fashion · Nightwear',
      avant: 'assets/demo/avant-pyjama.jpg',
      reference: 'assets/demo/ref-pyjama.jpg',
      apres: 'assets/demo/apres-pyjama.jpg',
      transformation:
        'The supplier photo becomes a morning scene in a cosy bedroom, worn by an African model. Perfect for a TikTok ad or a product page.',
      lienAlibaba:
        'https://www.alibaba.com/product-detail/Women-s-Pink-Contrast-Trim-Coral_1601966295026.html?spm=a27aq.27095423.1978240560.30.78372277xoCTC3',
    },
    {
      id: 'deodorant',
      tab: 'Deodorant',
      produit: 'Sakura roll-on deodorant',
      categorie: 'Beauty · Care',
      avant: 'assets/demo/avant-deodorant.jpg',
      reference: 'assets/demo/ref-deodorant.jpg',
      apres: 'assets/demo/apres-deodorant.jpg',
      transformation:
        'Pack kept exactly as is, held in a bright bathroom. The visual inspires trust and makes you want to try it.',
      lienAlibaba:
        'https://www.alibaba.com/product-detail/Laikou-Japan-Sakura-Vegan-Roll-On_1601828760102.html?spm=a2700.prosearch.normal_offer.d_image.796c67afpdukEM&priceId=f4aa4492db9949d0a8a7636f752e40ce',
    },
    {
      id: 'dentifrice',
      tab: 'Toothpaste',
      produit: 'ELAIMEI toothpaste',
      categorie: 'Beauty · Hygiene',
      avant: 'assets/demo/avant-dentifrice.jpg',
      reference: 'assets/demo/ref-dentifrice.jpg',
      apres: 'assets/demo/apres-dentifrice.jpg',
      transformation:
        'Bright-smile staging in natural light: the tube stays true while the setting sells the promised result.',
      lienAlibaba:
        'https://www.alibaba.com/product-detail/ELAIMEI-Oral-Care-Original-SP-4_1601574049387.html?spm=a27aq.30321987.6380511580.2.59ce56b5rsBKn6',
    },
    {
      id: 'sport',
      tab: 'Fitness',
      produit: 'Portable ab machine',
      categorie: 'Sports · Fitness',
      avant: 'assets/demo/avant-sport.jpg',
      reference: 'assets/demo/ref-sport.jpg',
      apres: 'assets/demo/apres-sport.jpg',
      transformation:
        'A technical supplier photo turned into an at-home demo: you get the product in one second — perfect for a video or carousel.',
      lienAlibaba:
        'https://www.alibaba.com/product-detail/Portable-Durable-Abdominal-Crunch-Machine-Slim_1601857652217.html?spm=a2700.galleryofferlist.normal_offer.d_image.59ba13a0K5WNxY&priceId=e8f51ab8088d496f8e9dbc0792f13101',
    },
  ];

  protected readonly selectedId = signal('pyjama');
  protected readonly comparePos = signal(50);

  protected selectedDemo(): Demo {
    return this.demos.find((d) => d.id === this.selectedId()) ?? this.demos[0];
  }

  protected select(id: string): void {
    this.selectedId.set(id);
  }

  protected onCompareInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.comparePos.set(Number(input.value));
  }
}
