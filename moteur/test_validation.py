"""Valide le moteur contre les classeurs de Léandre.

Usage (depuis le dossier oeufs) :  python moteur/test_validation.py
Attendu :
  - total 2027 : 43 816 871,364 œufs, écart nul
  - semaines 46 à 53 de 2026 : 6 304 548 œufs, écart nul
"""
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from moteur_prevision import Charte, Troupeau, prevision_periode  # noqa: E402

EXEMPLES = ICI.parent / "fichiers exemples"
CHARTE = Charte.depuis_json(ICI / "curves.json", "2027")
C4 = 448  # plafond d'âge du classeur 2026 (64 semaines)


def lignes(ws, r1, r2, colonnes):
    for row in ws.iter_rows(min_row=r1, max_row=r2, values_only=True):
        yield [row[c - 1] for c in colonnes]


def test_2027():
    wb = openpyxl.load_workbook(EXEMPLES / "Prev heb 2027 scott.xlsx", data_only=True, read_only=True)
    debut, fin = date(2026, 12, 31), date(2027, 12, 31)
    tot_classeur = tot_moteur = 0.0
    n = 0
    for a, b, c, g in lignes(wb["PREV2027"], 8, 68, (1, 2, 3, 7)):
        if not isinstance(a, datetime) or not isinstance(c, (int, float)) or g is None:
            continue
        t = Troupeau(str(b), a.date(), float(c), age_abattage_semaines=62)
        tot_classeur += g
        tot_moteur += prevision_periode(CHARTE, t, debut, fin)
        n += 1
    print(f"2027 : {n} troupeaux | classeur {tot_classeur:,.3f} | moteur {tot_moteur:,.3f} | écart {tot_moteur - tot_classeur:.6f}")
    assert abs(tot_moteur - tot_classeur) < 0.01


def test_2026_sem_46_53():
    wb = openpyxl.load_workbook(EXEMPLES / "Prev heb 2026 scott.xlsx", data_only=True, read_only=True)
    tot_classeur = tot_moteur = 0.0
    for sem in range(46, 54):
        fin = date(2025, 12, 27) + timedelta(days=7 * sem)
        debut = fin - timedelta(days=7)
        for a, c, d, g in lignes(wb[str(sem)], 8, 69, (1, 3, 4, 7)):
            if not isinstance(a, datetime) or not isinstance(c, (int, float)):
                continue
            plafond = C4 if not isinstance(d, datetime) else min((d.date() - a.date()).days, C4)
            t = Troupeau("?", a.date(), float(c), date_abattage=a.date() + timedelta(days=plafond))
            tot_classeur += g or 0
            tot_moteur += prevision_periode(CHARTE, t, debut, fin)
    print(f"2026 sem. 46-53 : classeur {tot_classeur:,.0f} | moteur {tot_moteur:,.0f} | écart {tot_moteur - tot_classeur:.3f}")
    assert abs(tot_moteur - tot_classeur) < 0.5


if __name__ == "__main__":
    test_2027()
    test_2026_sem_46_53()
    print("OK")
