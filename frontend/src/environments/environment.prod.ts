// Build production (Docker) : même origine, le nginx du conteneur
// proxie /api/* et /static/* vers le backend. Pas de nom de domaine requis.
export const environment = {
  apiBaseUrl: '',
};
