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
      tab: 'Pyjama',
      produit: 'Pyjama pilou rose',
      categorie: 'Mode · Nuit',
      avant: 'assets/demo/avant-pyjama.jpg',
      reference: 'assets/demo/ref-pyjama.jpg',
      apres: 'assets/demo/apres-pyjama.jpg',
      transformation:
        'La photo fournisseur devient une scène du matin dans une chambre cosy, portée par une mannequin africaine. Idéal pour une pub TikTok ou une fiche produit.',
      lienAlibaba:
        'https://www.alibaba.com/product-detail/Women-s-Pink-Contrast-Trim-Coral_1601966295026.html?spm=a27aq.27095423.1978240560.30.78372277xoCTC3',
    },
    {
      id: 'deodorant',
      tab: 'Déodorant',
      produit: 'Déodorant bille Sakura',
      categorie: 'Beauté · Soin',
      avant: 'assets/demo/avant-deodorant.jpg',
      reference: 'assets/demo/ref-deodorant.jpg',
      apres: 'assets/demo/apres-deodorant.jpg',
      transformation:
        'Pack produit conservé à l’identique, mis en main dans une salle de bain lumineuse. Le visuel inspire confiance et donne envie de tester.',
      lienAlibaba:
        'https://www.alibaba.com/product-detail/Laikou-Japan-Sakura-Vegan-Roll-On_1601828760102.html?spm=a2700.prosearch.normal_offer.d_image.796c67afpdukEM&priceId=f4aa4492db9949d0a8a7636f752e40ce',
    },
    {
      id: 'dentifrice',
      tab: 'Dentifrice',
      produit: 'Dentifrice ELAIMEI',
      categorie: 'Beauté · Hygiène',
      avant: 'assets/demo/avant-dentifrice.jpg',
      reference: 'assets/demo/ref-dentifrice.jpg',
      apres: 'assets/demo/apres-dentifrice.jpg',
      transformation:
        'Mise en scène sourire éclatant en lumière naturelle : le tube reste fidèle pendant que le décor vend le résultat promis.',
      lienAlibaba:
        'https://www.alibaba.com/product-detail/ELAIMEI-Oral-Care-Original-SP-4_1601574049387.html?spm=a27aq.30321987.6380511580.2.59ce56b5rsBKn6',
    },
    {
      id: 'sport',
      tab: 'Appareil sport',
      produit: 'Appareil abdominal portable',
      categorie: 'Sport · Fitness',
      avant: 'assets/demo/avant-sport.jpg',
      reference: 'assets/demo/ref-sport.jpg',
      apres: 'assets/demo/apres-sport.jpg',
      transformation:
        'Photo technique du fournisseur transformée en démonstration d’usage à domicile : on comprend le produit en une seconde, parfait pour une vidéo ou un carrousel.',
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
