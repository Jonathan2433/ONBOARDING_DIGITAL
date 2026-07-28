/**
 * Point d'entree du frontend.
 *
 * LOT 1, sous-etape T5, story MVP-L01-US002.
 *
 * L'element hote est cherche explicitement et son absence leve : monter dans le
 * vide produirait une page blanche silencieuse, precisement ce que le cahier
 * §17.4 interdit. Ici l'echec est bruyant et immediat.
 */
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './App';
import './styles.css';

const hote = document.getElementById('racine');
if (hote === null) {
  throw new Error('element hote « racine » absent de index.html : rien a monter');
}

createRoot(hote).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
