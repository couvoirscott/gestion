"""Moteur de prévision de production d'œufs d'incubation — Couvoir Scott.

Reconstruit à partir des classeurs Prev_heb_2026/2027/2028_scott.xlsx de Léandre.

Logique (validée) :
  production d'une semaine = poules effectives × gain de la charte sur la semaine
  gain = cumul(âge en fin de semaine) − cumul(âge en début de semaine)
  âges en jours depuis la date d'entrée (arrivée des poussins d'un jour), plafonnés à l'abattage
  cumul(âge) : lecture dans la charte (table AGE JR / CUMULATIF), âge minimum 174 jours,
  recherche approchée (plus grand âge <= valeur), dernière ligne au-delà de 468 jours.

Poules effectives :
  1. départ : quantité de la cédule d'achat (poussins d'un jour)
  2. vers 21 semaines : quantité transférée (Azur)
  3. dès ~33 semaines : recalibrage hebdomadaire = œufs réels ÷ gain de la charte
"""
from __future__ import annotations

import json
from bisect import bisect_right
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

AGE_MIN_CHARTE = 174  # jours : en dessous, le classeur lit la ligne 174
DEFAUT_ABATTAGE_SEMAINES = 63


class Charte:
    """Charte de ponte : cumul d'œufs par poule selon l'âge en jours."""

    def __init__(self, lignes):
        # lignes : [(age_jr, production_jour, cumulatif), ...] triées par âge
        self.ages = [int(a) for a, _, _ in lignes]
        self.cumul = [float(c) for _, _, c in lignes]

    @classmethod
    def depuis_json(cls, chemin: str | Path, annee: str = "2027") -> "Charte":
        data = json.loads(Path(chemin).read_text())
        return cls(data[annee])

    def cumul_a(self, age_jours: float) -> float:
        age = max(int(age_jours), AGE_MIN_CHARTE)
        i = bisect_right(self.ages, age) - 1
        return self.cumul[max(i, 0)]

    def gain(self, age_debut: float, age_fin: float) -> float:
        return self.cumul_a(age_fin) - self.cumul_a(age_debut)


@dataclass
class Troupeau:
    numero: str
    date_entree: date              # arrivée des poussins d'un jour
    poules: float                  # poules effectives de départ (cédule)
    date_abattage: Optional[date] = None   # date donnée par l'abattoir (prioritaire)
    age_abattage_semaines: Optional[int] = None  # âge choisi pour ce troupeau

    def age_abattage_jours(self, defaut_semaines: int = DEFAUT_ABATTAGE_SEMAINES) -> int:
        """Priorité : date de l'abattoir > âge choisi > âge par défaut."""
        if self.date_abattage is not None:
            return (self.date_abattage - self.date_entree).days
        semaines = self.age_abattage_semaines or defaut_semaines
        return semaines * 7


def age_plafonne(troupeau: Troupeau, jour: date, defaut_semaines: int = DEFAUT_ABATTAGE_SEMAINES) -> int:
    return min((jour - troupeau.date_entree).days, troupeau.age_abattage_jours(defaut_semaines))


def gain_periode(charte: Charte, troupeau: Troupeau, debut: date, fin: date,
                 defaut_semaines: int = DEFAUT_ABATTAGE_SEMAINES) -> float:
    """Gain de charte par poule entre deux dates (comme les colonnes M, N, O du classeur)."""
    return charte.gain(age_plafonne(troupeau, debut, defaut_semaines),
                       age_plafonne(troupeau, fin, defaut_semaines))


def prevision_periode(charte: Charte, troupeau: Troupeau, debut: date, fin: date,
                      poules: Optional[float] = None,
                      defaut_semaines: int = DEFAUT_ABATTAGE_SEMAINES) -> float:
    """Œufs prévus pour un troupeau entre deux dates (jamais négatif)."""
    n = troupeau.poules if poules is None else poules
    return max(0.0, n * gain_periode(charte, troupeau, debut, fin, defaut_semaines))


def poules_calibrees(charte: Charte, troupeau: Troupeau, fin_semaine: date, oeufs_reels: float,
                     defaut_semaines: int = DEFAUT_ABATTAGE_SEMAINES) -> Optional[float]:
    """Poules effectives implicites = œufs réels ÷ gain de la charte de la semaine."""
    debut = fin_semaine - timedelta(days=7)
    g = gain_periode(charte, troupeau, debut, fin_semaine, defaut_semaines)
    if g <= 0 or oeufs_reels <= 0:
        return None
    return oeufs_reels / g
