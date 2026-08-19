"""`person` — l'identite globale d'une personne.

LOT 2, sous-etape `T3`, story `MVP-L02-US002`.

FONDEMENT — modele de donnees §6.1, contraintes du §25.1, arbitrage
`ARB-DATA-001` : « conserver une identite globale unique et placer toutes les
donnees locales dans l'appartenance a l'entite ».

`person` EST GLOBALE. Elle ne porte donc PAS `entity_id`, et le mixin
`RessourceLocale` ne s'y applique pas. Tout ce qui est propre a une entite --
metier, statut professionnel, cercle, DSM -- vit dans `entity_membership` et ses
satellites, a partir de `T4`.

AUCUNE TABLE D'AUTHENTIFICATION ICI. Le §28 du modele groupe « `person` et
authentification » a son point 3, mais c'est un ordre GLOBAL sur dix-sept etapes
couvrant tous les lots : il dit ou placer l'authentification quand on y arrivera,
pas qu'il faut la faire maintenant. `user_account`, `magic_link_request`,
`user_session` et `auth_event` appartiennent au **LOT 3**. Rien ne les exige plus
tot : c'est `user_account` qui reference `person`, jamais l'inverse.

DEUX PASSAGES DU CORPUS A CONCILIER, ET LA LECTURE RETENUE.

  Le §6.1 exige « unicite INSENSIBLE A LA CASSE de `email_normalized` ». Le §25.1
  ecrit `person(email_normalized) UNIQUE`, c'est-a-dire un index SIMPLE, qui est
  sensible a la casse.

  Les deux se concilient sans choisir : une contrainte exige que la valeur
  STOCKEE soit deja en minuscules. L'insensibilite devient alors structurelle --
  deux graphies du meme e-mail ne peuvent pas coexister, puisque l'une des deux
  ne peut pas etre ecrite -- et l'index simple du §25.1 suffit.

  C'est plus fort qu'un index fonctionnel sur `lower(email_normalized)` : celui-ci
  empecherait le doublon mais laisserait entrer une valeur non normalisee, alors
  que la colonne s'appelle `_normalized`.

CE QUE LA NORMALISATION NE FAIT PAS, ET C'EST DELIBERE. Elle met en minuscules et
retire les espaces de bordure. Elle ne retire PAS les points, ne coupe PAS a un
`+`, et ne touche a aucune particularite de fournisseur. Ces regles-la
fusionneraient des personnes DISTINCTES, et aucun document du corpus ne les
demande.

UNE REGLE DU §6.1 QUI N'EST PAS DE CETTE SOUS-ETAPE : « le nom et l'e-mail ne
sont pas dupliques dans les tables d'appartenance ». Elle porte sur
`entity_membership`, qui n'existe pas encore -- sous-etape `T4`.
"""

from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import CheckConstraint, DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.modele import Base, ChampsCommuns, contrainte_enumeration


class EtatCompte(enum.StrEnum):
    """Les cinq valeurs du §6.1, dans l'ordre du cycle de vie.

    `ANONYMIZED` est terminal : le §6.1 pose qu'« une personne anonymisee ne peut
    pas etre reactivee sans creation d'une nouvelle identite ». La regle est
    portee par un declencheur, la migration `0004` -- une contrainte de ligne ne
    voit pas l'etat PRECEDENT.
    """

    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEPARTED = "departed"
    ANONYMIZED = "anonymized"


ETATS_COMPTE: tuple[str, ...] = tuple(membre.value for membre in EtatCompte)


def normaliser_email(valeur: str) -> str:
    """Forme normalisee d'une adresse : minuscules, sans espaces de bordure.

    C'est la SEULE normalisation appliquee, et son etroitesse est un choix. Voir
    l'en-tete du module : retirer les points ou couper a un `+` fusionnerait des
    personnes distinctes, et aucun document du corpus ne le demande.

    La contrainte `email_normalise_en_minuscules` en base refuse toute valeur que
    cette fonction n'aurait pas produite. Le controle ne depend donc pas de la
    discipline de l'appelant.
    """
    return valeur.strip().lower()


class Person(ChampsCommuns, Base):
    """Identite globale d'une personne — modele §6.1."""

    __tablename__ = "person"

    #  `email` est la valeur d'AFFICHAGE, §6.1 : la casse que la personne emploie
    #  pour elle-meme. Elle n'est pas unique -- c'est `email_normalized` qui
    #  porte l'unicite -- et elle n'est pas normalisee, sinon elle ne servirait a
    #  rien.
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    email_normalized: Mapped[str] = mapped_column(String(320), nullable=False)

    first_name: Mapped[str] = mapped_column(Text, nullable=False)
    last_name: Mapped[str] = mapped_column(Text, nullable=False)
    preferred_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    account_state: Mapped[str] = mapped_column(String(16), nullable=False)

    anonymized_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        #  §25.1 : `person(email_normalized) UNIQUE`, index SIMPLE. Il suffit
        #  parce que la contrainte suivante interdit d'y ecrire deux graphies.
        UniqueConstraint("email_normalized", name="email_normalized_unique"),
        #  L'insensibilite a la casse du §6.1, rendue structurelle.
        CheckConstraint(
            "email_normalized = lower(email_normalized)",
            name="email_normalise_en_minuscules",
        ),
        #  La part STRICTEMENT verifiable de la forme d'une adresse : pas
        #  d'espace, et une arobase qui n'est pas en premiere position. Aucune
        #  validation plus poussee : le corpus n'en prescrit aucune, et une
        #  expression pretendant valider une adresse selon la RFC rejette des
        #  adresses legitimes -- un refus a l'import du LOT 9 coute plus cher
        #  qu'une adresse mal formee stockee.
        CheckConstraint(
            "email_normalized !~ '\\s' AND position('@' IN email_normalized) > 1",
            name="email_normalise_plausible",
        ),
        contrainte_enumeration("account_state", EtatCompte, "account_state_valide"),
        #  Coherence entre l'etat et l'horodatage. DERIVEE, non ecrite telle
        #  quelle : le §6.1 declare les deux colonnes sans lier leurs valeurs.
        #  Une personne `anonymized` sans horodatage rendrait le LOT 10 incapable
        #  de dire QUAND l'anonymisation a eu lieu, ce que le RGPD exige de
        #  tracer ; et un horodatage sans l'etat decrirait une anonymisation qui
        #  n'a pas pris.
        CheckConstraint(
            "(account_state = 'anonymized') = (anonymized_at IS NOT NULL)",
            name="anonymisation_coherente",
        ),
    )
